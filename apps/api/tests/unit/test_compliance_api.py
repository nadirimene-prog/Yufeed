import pytest
from datetime import datetime, timedelta, timezone

from src.models import models


@pytest.mark.unit
class TestComplianceAPI:
    def test_analyze_document_and_annotations(self, client, db_session, monkeypatch, admin_headers):
        celex = "CELEX-TEST-1"
        doc = models.LegalDocument(
            celex=celex,
            title="AML Regulation",
            publication_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            full_text="Sample text",
            article_breakdown=[{"number": "1", "content": "Banks shall..."}],
        )
        db_session.add(doc)
        db_session.commit()

        from src.api import compliance as compliance_api

        monkeypatch.setattr(
            compliance_api,
            "analyze_document",
            lambda data: {
                "compliance_domain": "aml",
                "risk_level": "high",
                "obligations_json": [{"obligation": "Test"}],
                "implementation_deadline": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "ai_summary": "summary",
                "analyzed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            },
        )
        monkeypatch.setattr(
            compliance_api, "seed_obligations_for_doc", lambda *args, **kwargs: None
        )

        resp = client.post(
            f"/api/compliance/documents/{celex}/analyze",
            json={"force": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Analysis complete"

        # Create annotation
        resp = client.post(
            f"/api/compliance/documents/{celex}/annotations",
            json={
                "content": "Note",
                "article_reference": "Art 1",
                "user_email": "user@example.com",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        annotation_id = resp.json()["id"]

        # List annotations
        resp = client.get(f"/api/compliance/documents/{celex}/annotations", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Delete annotation
        resp = client.delete(f"/api/compliance/annotations/{annotation_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Annotation deleted"

    def test_compliance_dashboard_and_filters(self, client, db_session, admin_headers):
        now = datetime.now(timezone.utc)
        doc_high = models.LegalDocument(
            celex="CELEX-HIGH",
            title="High Risk Regulation",
            publication_date=now - timedelta(days=10),
            risk_level="high",
            compliance_domain="aml",
            implementation_deadline=now + timedelta(days=10),
        )
        doc_low = models.LegalDocument(
            celex="CELEX-LOW",
            title="Low Risk Notice",
            publication_date=now - timedelta(days=20),
            risk_level="low",
            compliance_domain="payments",
            implementation_deadline=now + timedelta(days=120),
        )
        db_session.add_all([doc_high, doc_low])
        db_session.commit()

        resp = client.get("/api/compliance/dashboard/metrics", headers=admin_headers)
        assert resp.status_code == 200
        metrics = resp.json()
        assert metrics["total_documents"] >= 2
        assert metrics["high_risk_count"] >= 1

        resp = client.get("/api/compliance/documents/high-risk", headers=admin_headers)
        assert resp.status_code == 200
        assert any(doc["celex"] == "CELEX-HIGH" for doc in resp.json())

        resp = client.get(
            "/api/compliance/documents/deadlines",
            params={"days": 30},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert any(doc["celex"] == "CELEX-HIGH" for doc in resp.json())

    def test_document_timeline_returns_publication_relation_and_version_events(
        self, client, db_session, admin_headers
    ):
        doc = models.LegalDocument(
            celex="CELEX-TL-1",
            title="Primary Act",
            publication_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            entry_into_force_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
            last_modified=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        related = models.LegalDocument(
            celex="CELEX-TL-2",
            title="Amending Act",
            publication_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
            last_modified=datetime(2024, 3, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([doc, related])
        db_session.commit()

        relation = models.LegalRelation(
            from_doc_id=related.id,
            relation_type="work_amends_work",
            to_doc_id=doc.id,
        )
        version = models.LegalVersion(
            doc_id=doc.id,
            kind=models.VersionKind.CORRIGENDUM.value,
            language="en",
            retrieved_at=datetime(2024, 4, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([relation, version])
        db_session.commit()

        resp = client.get(
            f"/api/compliance/documents/{doc.celex}/timeline",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        assert events

        event_types = {event["type"] for event in events}
        assert "PUBLICATION" in event_types
        assert "ENTRY_INTO_FORCE" in event_types
        assert "AMENDMENT" in event_types
        assert "CORRIGENDUM" in event_types
        assert any(event.get("related_doc_celex") == related.celex for event in events)

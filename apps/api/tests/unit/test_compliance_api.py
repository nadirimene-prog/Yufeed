import pytest
from datetime import datetime, timedelta, timezone

from src.models import models
from src.models import compliance as comp_models


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

    def test_kyc_reviews_due_set_cdd_and_initiate_review(self, client, db_session, admin_headers):
        create_resp = client.post(
            "/api/compliance/kyc",
            json={
                "type": "kyc",
                "first_name": "Review",
                "last_name": "User",
                "email": "review.user@example.com",
            },
            headers=admin_headers,
        )
        assert create_resp.status_code == 200
        profile_id = create_resp.json()["id"]

        profile = (
            db_session.query(comp_models.KYCProfile)
            .filter(comp_models.KYCProfile.id == profile_id)
            .first()
        )
        profile.status = comp_models.ComplianceStatus.APPROVED.value
        profile.next_review_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        due_resp = client.get("/api/compliance/kyc/reviews-due", headers=admin_headers)
        assert due_resp.status_code == 200
        payload = due_resp.json()
        assert payload["total_due"] >= 1
        assert any(item["id"] == profile_id for item in payload["items"])

        cdd_resp = client.post(
            f"/api/compliance/kyc/{profile_id}/set-cdd-level",
            json={"cdd_level": "enhanced", "reason": "manual escalation"},
            headers=admin_headers,
        )
        assert cdd_resp.status_code == 200
        assert cdd_resp.json()["cdd_level"] == "enhanced"
        assert cdd_resp.json()["cdd_reason"] == "manual escalation"

        review_resp = client.post(
            f"/api/compliance/kyc/{profile_id}/initiate-review",
            headers=admin_headers,
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == "manual_review"
        assert review_resp.json()["profile_id"] == profile_id

    def test_kyc_screen_and_verify_document_endpoints(self, client, admin_headers, monkeypatch):
        create_resp = client.post(
            "/api/compliance/kyc",
            json={
                "type": "kyc",
                "first_name": "Screen",
                "last_name": "User",
                "email": "screen.user@example.com",
            },
            headers=admin_headers,
        )
        assert create_resp.status_code == 200
        profile_id = create_resp.json()["id"]

        from src.api import compliance as compliance_api

        now = datetime.now(timezone.utc)
        monkeypatch.setattr(
            compliance_api.KYCOnboardingService,
            "screen_customer",
            lambda self, profile_id, tenant_id=None: {
                "profile_id": profile_id,
                "sanctions_status": "clear",
                "screened_at": now,
                "is_hit": False,
                "highest_score": 0.0,
                "match_count": 0,
                "findings_created": 0,
            },
        )
        monkeypatch.setattr(
            compliance_api.KYCOnboardingService,
            "verify_documents",
            lambda self, profile_id, tenant_id=None: {
                "profile_id": profile_id,
                "processed_count": 0,
                "verified_count": 0,
                "rejected_count": 0,
                "error_count": 0,
                "findings_created": 0,
                "documents": [],
            },
        )

        screen_resp = client.post(f"/api/compliance/kyc/{profile_id}/screen", headers=admin_headers)
        assert screen_resp.status_code == 200
        assert screen_resp.json()["profile_id"] == profile_id
        assert screen_resp.json()["sanctions_status"] == "clear"

        verify_resp = client.post(
            f"/api/compliance/kyc/{profile_id}/verify-documents",
            headers=admin_headers,
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["profile_id"] == profile_id
        assert verify_resp.json()["processed_count"] == 0

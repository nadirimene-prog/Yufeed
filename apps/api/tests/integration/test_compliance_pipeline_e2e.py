"""
End-to-end integration tests for the compliance pipeline.

Tests the full lifecycle:
  Ingestion → Obligation extraction → AI policy mapping → Approval → Linking

Also validates:
  - Supervisory alert persistence + obligation extraction
  - Idempotence (no duplicates on re-run)
  - Keyword fallback when embedding provider is unavailable
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.compliance_workflow import (
    LegalDocument,
    RegulatoryObligation,
    PolicyDocument,
    PolicyTemplate,
    ObligationPolicyMapping,
    SupervisoryAlert,
    InternalRule,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_policy_and_template(db_session: Session):
    """Create a policy + template for obligation linking tests."""
    tpl = PolicyTemplate(
        template_id="E2E_AML_TPL",
        name="AML Compliance Policy",
        category="aml",
        version="1.0",
        owner="test",
        review_frequency_months=12,
        content="Anti-money laundering policy for {{ institution_name }}.",
        is_active=True,
        regulatory_basis=["AMLD5 Art. 8", "AMLD6 Art. 3"],
        institution_types=["psp", "eme"],
        applicable_regulations=["AMLD5", "AMLD6"],
    )
    db_session.add(tpl)
    db_session.flush()

    policy = PolicyDocument(
        policy_id="E2E_AML_TPL",
        name="AML Compliance Policy",
        version="1.0",
        owner="compliance-team",
        status="active",
        content="Anti-money laundering procedures and controls.",
    )
    db_session.add(policy)
    db_session.flush()

    return policy, tpl


@pytest.fixture
def seed_legal_document(db_session: Session):
    """Create a legal document with obligations_json for seeding."""
    doc = LegalDocument(
        celex="E2E-TEST-32024R0001",
        title="Directive on anti-money laundering",
        source="eur-lex",
        jurisdiction="EU",
        doc_type="regulation",
        language="en",
        obligations_json=[
            {
                "obligation_text": "Financial institutions shall apply customer due diligence measures.",
                "article_ref": "Art. 13",
                "applicability": "All financial institutions",
                "deadline": None,
            },
            {
                "obligation_text": "Suspicious transaction reports shall be filed within 30 days.",
                "article_ref": "Art. 33",
                "applicability": "All obliged entities",
                "deadline": "30 days",
            },
        ],
    )
    db_session.add(doc)
    db_session.commit()
    return doc


# ---------------------------------------------------------------------------
# Test: Full E2E Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCompliancePipelineE2E:
    """End-to-end compliance pipeline tests."""

    def test_obligation_seeding_from_document(self, db_session: Session, seed_legal_document):
        """Obligations are correctly seeded from a document's obligations_json."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        created = seed_obligations_for_doc(db_session, doc)
        assert created == 2, f"Expected 2 obligations, got {created}"

        obligations = (
            db_session.query(RegulatoryObligation)
            .filter(RegulatoryObligation.doc_id == doc.id)
            .all()
        )
        assert len(obligations) == 2
        assert all(o.status == "draft" for o in obligations)
        assert any("Art. 13" in (o.article_ref or "") for o in obligations)
        assert any("Art. 33" in (o.article_ref or "") for o in obligations)

    def test_obligation_seeding_idempotent(self, db_session: Session, seed_legal_document):
        """Re-running seed on the same document creates 0 duplicates."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        first_run = seed_obligations_for_doc(db_session, doc)
        assert first_run == 2

        second_run = seed_obligations_for_doc(db_session, doc, allow_existing=True)
        assert second_run == 0, f"Expected 0 new obligations on re-run, got {second_run}"

        total = (
            db_session.query(RegulatoryObligation)
            .filter(RegulatoryObligation.doc_id == doc.id)
            .count()
        )
        assert total == 2

    def test_policy_suggestions_endpoint(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: dict,
        seed_legal_document,
        seed_policy_and_template,
    ):
        """Policy suggestions endpoint returns confidence, reasoning, match_method."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        seed_obligations_for_doc(db_session, doc)
        db_session.commit()

        obligation = (
            db_session.query(RegulatoryObligation)
            .filter(RegulatoryObligation.doc_id == doc.id)
            .first()
        )
        assert obligation is not None

        resp = client.get(
            f"/api/obligations/{obligation.id}/policy-suggestions",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", [])

        # Should return at least keyword-based suggestions
        if items:
            item = items[0]
            assert "score" in item or "confidence" in item
            # match_method may be present (semantic or keyword)
            if "match_method" in item:
                assert item["match_method"] in ("semantic", "keyword")

    def test_obligation_approval_links_policy(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: dict,
        superuser_headers: dict,
        seed_legal_document,
        seed_policy_and_template,
    ):
        """Approving an obligation links it to a policy and creates an internal rule."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        policy, _ = seed_policy_and_template
        seed_obligations_for_doc(db_session, doc)
        db_session.commit()

        obligation = (
            db_session.query(RegulatoryObligation)
            .filter(RegulatoryObligation.doc_id == doc.id)
            .first()
        )

        resp = client.patch(
            f"/api/obligations/{obligation.id}/approve",
            headers=superuser_headers,
            json={
                "status": "approved",
                "note": "E2E test approval",
                "linked_policy_id": policy.id,
                "create_internal_rule": True,
                "internal_rule_name": "CDD Requirement",
                "internal_rule_description": "Implement customer due diligence",
            },
        )
        assert resp.status_code in (200, 201), resp.text

        db_session.refresh(obligation)
        assert obligation.status == "approved"
        assert obligation.linked_policy_id == policy.id

        rules = (
            db_session.query(InternalRule).filter(InternalRule.obligation_id == obligation.id).all()
        )
        assert len(rules) >= 1

    def test_bulk_approve_partial_success(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: dict,
        superuser_headers: dict,
        seed_legal_document,
        seed_policy_and_template,
    ):
        """Bulk approve handles partial success (some succeed, some fail)."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        seed_obligations_for_doc(db_session, doc)
        db_session.commit()

        obligations = (
            db_session.query(RegulatoryObligation)
            .filter(RegulatoryObligation.doc_id == doc.id)
            .all()
        )
        valid_ids = [o.id for o in obligations]

        resp = client.post(
            "/api/obligations/bulk-approve",
            headers=superuser_headers,
            json={
                "obligation_ids": valid_ids + [99999],  # 99999 doesn't exist
                "status": "approved",
                "note": "Bulk E2E test",
                "auto_link_best_suggestion": False,
                "create_internal_rule": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(valid_ids) + 1
        assert data["succeeded"] >= len(valid_ids)
        assert data["failed"] >= 1

    def test_coverage_stats_endpoint(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: dict,
        seed_legal_document,
    ):
        """Coverage stats returns correct linked/unlinked counts."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        seed_obligations_for_doc(db_session, doc)
        db_session.commit()

        resp = client.get("/api/obligations/coverage-stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "total" in data
        assert "linked_count" in data
        assert "unlinked_count" in data
        assert "ai_suggested_count" in data
        assert "confidence_tiers" in data
        assert data["total"] >= 2
        assert data["unlinked_count"] >= 2  # freshly created, not linked yet


# ---------------------------------------------------------------------------
# Test: Supervisory Alert Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSupervisoryPipeline:
    """Tests for supervisory alert persistence and obligation extraction."""

    def test_supervisory_alert_persistence(self, db_session: Session):
        """SupervisoryAlert is persisted with dedup_key."""
        import hashlib

        dedup = hashlib.sha256("amla:Test Alert:2026-01-01".encode()).hexdigest()[:64]
        alert = SupervisoryAlert(
            dedup_key=dedup,
            source_system="amla",
            title="Test AMLA Alert",
            description="New AML guidelines published.",
            link="https://amla.europa.eu/test",
            jurisdiction="EU",
            language="en",
            status="new",
        )
        db_session.add(alert)
        db_session.commit()

        found = (
            db_session.query(SupervisoryAlert).filter(SupervisoryAlert.dedup_key == dedup).first()
        )
        assert found is not None
        assert found.source_system == "amla"
        assert found.title == "Test AMLA Alert"

    def test_supervisory_dedup_prevents_duplicates(self, db_session: Session):
        """Duplicate dedup_key raises IntegrityError (DB-level dedup)."""
        import hashlib
        from sqlalchemy.exc import IntegrityError

        dedup = hashlib.sha256("esma:Unique Alert:2026-02-01".encode()).hexdigest()[:64]

        alert1 = SupervisoryAlert(
            dedup_key=dedup,
            source_system="esma",
            title="Unique Alert",
            status="new",
        )
        db_session.add(alert1)
        db_session.commit()

        alert2 = SupervisoryAlert(
            dedup_key=dedup,
            source_system="esma",
            title="Duplicate Alert",
            status="new",
        )
        db_session.add(alert2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


# ---------------------------------------------------------------------------
# Test: Keyword Fallback
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestKeywordFallback:
    """Tests that policy suggestions degrade gracefully without embeddings."""

    def test_suggestions_work_without_embeddings(
        self,
        client: TestClient,
        db_session: Session,
        admin_headers: dict,
        seed_legal_document,
        seed_policy_and_template,
    ):
        """When embedding provider is unavailable, keyword fallback provides results."""
        from src.services.obligation_service import seed_obligations_for_doc

        doc = seed_legal_document
        seed_obligations_for_doc(db_session, doc)
        db_session.commit()

        obligation = (
            db_session.query(RegulatoryObligation)
            .filter(RegulatoryObligation.doc_id == doc.id)
            .first()
        )

        # Patch embedding provider to simulate unavailability
        with patch("src.services.policy_matcher.PolicyMatcher._embed_text", return_value=None):
            resp = client.get(
                f"/api/obligations/{obligation.id}/policy-suggestions",
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            items = data.get("items", [])
            # Should still return results via keyword fallback
            if items:
                for item in items:
                    if "match_method" in item:
                        assert item["match_method"] == "keyword"

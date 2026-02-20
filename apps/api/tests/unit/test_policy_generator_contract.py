"""
Contract tests for the Policy Generator API.

Verifies that the FE/BE contract is respected:
- ``variable_values`` is the canonical field; ``custom_variables`` is a deprecated alias.
- ``obligation_ids`` accepts both int and string values and normalises to ``List[int]``.
- Template variable responses include the full shape expected by the frontend.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.compliance_workflow import PolicyTemplate, RegulatoryObligation, LegalDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_template(db: Session) -> PolicyTemplate:
    """Create a minimal active policy template."""
    tpl = PolicyTemplate(
        template_id="CONTRACT_TEST_TPL",
        name="Contract Test Template",
        category="aml",
        version="1.0",
        owner="test",
        review_frequency_months=12,
        content="Policy for {{ institution_name }}.",
        is_active=True,
        regulatory_basis=["AMLD5 Art. 8"],
        institution_types=["psp"],
        applicable_regulations=["AMLD5"],
    )
    db.add(tpl)
    db.flush()
    return tpl


def _seed_obligation(db: Session) -> RegulatoryObligation:
    """Create a minimal obligation linked to a dummy document."""
    doc = LegalDocument(
        celex="TEST-CONTRACT-001",
        title="Contract test document",
        source="test",
        jurisdiction="EU",
    )
    db.add(doc)
    db.flush()

    obl = RegulatoryObligation(
        obligation_id="OBL-CONTRACT01",
        doc_id=doc.id,
        obligation_text="Financial institutions must report suspicious transactions.",
        article_ref="Art. 33",
        status="draft",
    )
    db.add(obl)
    db.flush()
    return obl


# ---------------------------------------------------------------------------
# Contract: POST /api/policy-generator/generate
# ---------------------------------------------------------------------------


class TestPolicyGeneratorPayloadContract:
    """Verify payload normalisation in PolicyGeneratePayload."""

    def test_variable_values_canonical(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """``variable_values`` is accepted as the canonical field."""
        tpl = _seed_template(db_session)
        obl = _seed_obligation(db_session)
        db_session.commit()

        resp = client.post(
            "/api/policy-generator/generate",
            headers=admin_headers,
            json={
                "template_id": tpl.template_id,
                "obligation_ids": [obl.id],
                "variable_values": {"institution_name": "ACME Corp"},
            },
        )
        # 200/201/202 all acceptable (generation may be async)
        assert resp.status_code in (200, 201, 202), resp.text

    def test_custom_variables_alias_accepted(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """``custom_variables`` is still accepted as a backward-compatible alias."""
        tpl = _seed_template(db_session)
        obl = _seed_obligation(db_session)
        db_session.commit()

        resp = client.post(
            "/api/policy-generator/generate",
            headers=admin_headers,
            json={
                "template_id": tpl.template_id,
                "obligation_ids": [obl.id],
                "custom_variables": {"institution_name": "Legacy Corp"},
            },
        )
        assert resp.status_code in (200, 201, 202), resp.text

    def test_obligation_ids_as_strings_cast(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """String obligation IDs are cast to int transparently."""
        tpl = _seed_template(db_session)
        obl = _seed_obligation(db_session)
        db_session.commit()

        resp = client.post(
            "/api/policy-generator/generate",
            headers=admin_headers,
            json={
                "template_id": tpl.template_id,
                "obligation_ids": [str(obl.id)],
                "variable_values": {},
            },
        )
        assert resp.status_code in (200, 201, 202), resp.text

    def test_obligation_ids_invalid_rejected(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """Non-numeric obligation IDs return 422."""
        tpl = _seed_template(db_session)
        db_session.commit()

        resp = client.post(
            "/api/policy-generator/generate",
            headers=admin_headers,
            json={
                "template_id": tpl.template_id,
                "obligation_ids": ["not-a-number"],
                "variable_values": {},
            },
        )
        assert resp.status_code == 422

    def test_obligation_ids_bool_rejected(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """Boolean obligation IDs are explicitly rejected."""
        tpl = _seed_template(db_session)
        db_session.commit()

        resp = client.post(
            "/api/policy-generator/generate",
            headers=admin_headers,
            json={
                "template_id": tpl.template_id,
                "obligation_ids": [True],
                "variable_values": {},
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Contract: GET /api/policy-generator/templates (response shape)
# ---------------------------------------------------------------------------


class TestPolicyGeneratorTemplateContract:
    """Verify the template listing / variables response shape."""

    def test_templates_list_returns_expected_fields(
        self, client: TestClient, db_session: Session, admin_headers: dict
    ):
        """Template list items have the fields the frontend expects."""
        _seed_template(db_session)
        db_session.commit()

        resp = client.get("/api/policy-generator/templates", headers=admin_headers)
        assert resp.status_code == 200

        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", data.get("templates", []))
        assert len(items) > 0, "Expected at least one template"

        tpl = items[0]
        # Mandatory fields for the frontend TemplateVariable display
        for field in ("template_id", "name", "category"):
            assert field in tpl, f"Missing field '{field}' in template response"

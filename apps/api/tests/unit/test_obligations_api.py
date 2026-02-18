import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from src.api import obligations as obligations_api
from src.auth.dependencies import CurrentUser
from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    InternalRule,
    RiskEntry,
    RiskCategory,
)
from src.models.models import LegalDocument
from src.schemas.obligation_schemas import ObligationUpdate, ObligationApproval


@pytest.mark.unit
@pytest.mark.asyncio
async def test_obligation_workflow_endpoints(db_session, monkeypatch):
    async def dummy_broadcast(*args, **kwargs):
        return None

    monkeypatch.setattr(obligations_api.ws_manager, "broadcast", dummy_broadcast)

    now = datetime.now(timezone.utc)
    doc = LegalDocument(
        celex="32024R7777",
        title="Payment services directive",
        jurisdiction="EU",
        source_system="eur-lex",
        publication_date=now,
        scope_tags=["psp"],
    )
    db_session.add(doc)
    db_session.commit()

    obligation = RegulatoryObligation(
        obligation_id="OBL-777",
        document=doc,
        obligation_text="Payment services must monitor transactions.",
        status="draft",
        created_by="user@example.com",
        scope_tags=["psp"],
        updated_at=now,
    )
    policy = PolicyDocument(
        policy_id="POL-777",
        name="AML Policy",
        status="draft",
        owner="compliance",
        updated_at=now,
    )
    category = RiskCategory(
        category_id="RISK-CAT-777",
        name="Compliance",
        description="Compliance risk",
        risk_level="high",
        status="active",
        created_at=now,
        updated_at=now,
    )
    risk_entry = RiskEntry(
        risk_id="RISK-777",
        category=category,
        name="KYC gaps",
        description="Missing KYC documents",
        inherent_risk_level="high",
        residual_risk_level="medium",
        mitigation_status="not_started",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([obligation, policy, category, risk_entry])
    db_session.commit()

    current_user = CurrentUser("user-1", "user@example.com", "admin")

    listing_with_counts = obligations_api.list_obligations(
        status=None,
        jurisdiction="EU",
        source_system="eur-lex",
        scope="psp",
        q="Payment",
        include_status_counts=True,
        skip=0,
        limit=10,
        db=db_session,
        _=None,
    )
    assert "status_counts" in listing_with_counts
    assert listing_with_counts["status_counts"].get("draft", 0) >= 1

    listing = obligations_api.list_obligations(
        status="draft",
        jurisdiction="EU",
        source_system="eur-lex",
        scope="psp",
        q="Payment",
        skip=0,
        limit=50,
        db=db_session,
        _=None,
    )
    assert listing["total"] >= 1

    updated = await obligations_api.update_obligation(
        obligation.id,
        ObligationUpdate(status="in_review", note="Review started"),
        db_session,
        current_user,
    )
    assert updated["status"] == "in_review"

    with pytest.raises(HTTPException) as exc_info:
        await obligations_api.approve_obligation(
            obligation.id,
            ObligationApproval(
                status="approved",
                note="Self approval attempt",
                linked_policy_id=policy.id,
            ),
            db_session,
            current_user,
        )
    assert exc_info.value.status_code == 409

    approver_user = CurrentUser("user-2", "approver@example.com", "admin")
    approved = await obligations_api.approve_obligation(
        obligation.id,
        ObligationApproval(
            status="approved",
            note="Approved",
            linked_policy_id=policy.id,
            create_internal_rule=True,
            internal_rule_name="IR for OBL",
            link_risk_entry_ids=[risk_entry.id],
        ),
        db_session,
        approver_user,
    )
    assert approved["status"] == "approved"
    assert approved.get("created_internal_rule")
    assert approved["approved_by"] == approver_user.email

    fetched = obligations_api.get_obligation(obligation.id, db_session, None)
    assert fetched["obligation_id"] == obligation.obligation_id

    risks = obligations_api.get_obligation_risks(obligation.id, db_session, None)
    assert risks["items"]

    internal_rules = obligations_api.get_obligation_internal_rules(obligation.id, db_session, None)
    assert internal_rules["items"]

    # Directly create an internal rule to cover listing path
    db_session.add(
        InternalRule(
            internal_rule_id="IR-EXTRA",
            obligation_id=obligation.id,
            name="Extra rule",
            status="draft",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    internal_rules = obligations_api.get_obligation_internal_rules(obligation.id, db_session, None)
    assert len(internal_rules["items"]) >= 1

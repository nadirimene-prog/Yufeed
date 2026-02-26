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


@pytest.mark.unit
def test_list_obligations_scope_validation_and_psan_alias(db_session):
    now = datetime.now(timezone.utc)
    doc = LegalDocument(
        celex="32024R9999",
        title="MiCA obligations for crypto-asset service providers",
        jurisdiction="EU",
        source_system="eur-lex",
        publication_date=now,
        scope_tags=["vasp"],
    )
    db_session.add(doc)
    db_session.commit()

    obligation = RegulatoryObligation(
        obligation_id="OBL-PSAN-1",
        doc_id=doc.id,
        celex=doc.celex,
        obligation_text="Crypto-asset service providers must maintain controls.",
        status="draft",
        scope_tags=["vasp"],
        updated_at=now,
    )
    db_session.add(obligation)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        obligations_api.list_obligations(
            status=None,
            jurisdiction=None,
            source_system=None,
            scope="aml",
            q=None,
            include_status_counts=False,
            tenant_id=None,
            skip=0,
            limit=20,
            db=db_session,
            _=None,
        )
    assert exc_info.value.status_code == 422

    listing = obligations_api.list_obligations(
        status="draft",
        jurisdiction="EU",
        source_system="eur-lex",
        scope="psan",
        q="crypto-asset",
        include_status_counts=False,
        tenant_id=None,
        skip=0,
        limit=20,
        db=db_session,
        _=None,
    )
    assert listing["total"] >= 1


@pytest.mark.unit
def test_obligations_grouped_by_regulation_and_coverage_endpoint(db_session):
    now = datetime.now(timezone.utc)
    doc = LegalDocument(
        celex="32024R1234",
        title="Markets in crypto-assets regulation",
        jurisdiction="EU",
        source_system="eur-lex",
        publication_date=now,
        scope_tags=["vasp"],
        article_breakdown=[
            {
                "number": "1",
                "title": "General obligations",
                "content": "Crypto-asset service providers shall maintain governance arrangements.",
            },
            {
                "number": "2",
                "title": "Notifications",
                "content": "Crypto-asset service providers must notify competent authorities.",
            },
            {
                "number": "3",
                "title": "Definitions",
                "content": "This Article defines terms used in this Regulation.",
            },
        ],
    )
    db_session.add(doc)
    db_session.commit()

    db_session.add_all(
        [
            RegulatoryObligation(
                obligation_id="OBL-MICA-1",
                doc_id=doc.id,
                celex=doc.celex,
                obligation_text="CASPs shall maintain governance arrangements.",
                article_ref="Article 1",
                status="draft",
                scope_tags=["vasp"],
                updated_at=now,
            ),
            RegulatoryObligation(
                obligation_id="OBL-MICA-2",
                doc_id=doc.id,
                celex=doc.celex,
                obligation_text="CASPs must notify competent authorities without delay.",
                article_ref="Article 2",
                status="in_review",
                scope_tags=["vasp"],
                updated_at=now,
            ),
            RegulatoryObligation(
                obligation_id="OBL-MICA-X",
                doc_id=doc.id,
                celex=doc.celex,
                obligation_text="CASPs shall document internal rationale.",
                article_ref=None,
                status="rejected",
                scope_tags=["vasp"],
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    grouped = obligations_api.list_obligations_by_regulation(
        status=None,
        jurisdiction="EU",
        source_system="eur-lex",
        scope="psan",
        q="CASP",
        include_status_counts=True,
        include_coverage=True,
        tenant_id=None,
        skip=0,
        limit=20,
        db=db_session,
        _=None,
    )

    assert grouped["total_regulations"] >= 1
    assert grouped["total_obligations"] >= 3
    assert grouped["status_counts"]["draft"] >= 1
    item = grouped["items"][0]
    assert item["document"]["id"] == doc.id
    assert item["filtered_obligation_count"] == 3
    assert item["obligation_counts"]["total"] == 3
    assert item["coverage"]["article_count"] == 3
    assert item["coverage"]["articles_with_obligation_signal"] == 2
    assert item["coverage"]["covered_signal_article_count"] == 2
    assert item["coverage"]["obligations_without_article_ref"] == 1

    coverage = obligations_api.get_regulation_obligation_coverage(
        document_id=doc.id,
        tenant_id=None,
        db=db_session,
        current_user=None,
    )
    assert coverage["document"]["celex"] == doc.celex
    assert coverage["obligation_counts"]["total"] == 3
    assert coverage["coverage"]["article_count"] == 3
    assert coverage["coverage"]["uncovered_signal_article_count"] == 0

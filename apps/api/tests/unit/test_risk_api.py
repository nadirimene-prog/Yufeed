import pytest
from datetime import datetime, timezone

from src.api import risk as risk_api
from src.auth.dependencies import CurrentUser
from src.models.compliance_workflow import RiskCategory, RiskEntry, RegulatoryObligation
from src.models.models import LegalDocument
from src.schemas.risk_schemas import (
    RiskCategoryCreate,
    RiskCategoryUpdate,
    RiskEntryCreate,
    RiskEntryUpdate,
    ObligationRiskLinkCreate,
)


@pytest.mark.unit
def test_risk_categories_and_tree(db_session):
    parent = RiskCategory(
        category_id="RISK-CAT-001",
        name="Operational",
        description="Ops risk",
        risk_level="medium",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    child = RiskCategory(
        category_id="RISK-CAT-002",
        name="Fraud",
        description="Fraud risk",
        parent=parent,
        risk_level="high",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([parent, child])
    db_session.commit()

    listing = risk_api.list_risk_categories(
        status=None,
        parent_id=None,
        db=db_session,
        _=None,
    )
    assert listing["items"]

    tree = risk_api.get_category_tree(db_session, None)
    assert tree["items"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_risk_entry_crud_and_links(db_session, monkeypatch):
    async def dummy_broadcast(*args, **kwargs):
        return None

    monkeypatch.setattr(risk_api.ws_manager, "broadcast", dummy_broadcast)

    category = RiskCategory(
        category_id="RISK-CAT-010",
        name="Compliance",
        description="Compliance risk",
        risk_level="high",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(category)
    db_session.commit()

    current_user = CurrentUser("user-1", "user@example.com", "admin")

    created_cat = await risk_api.create_risk_category(
        RiskCategoryCreate(
            name="Financial",
            description="Financial risk",
            parent_id=category.id,
            risk_level="medium",
            status="active",
        ),
        db_session,
        current_user,
    )
    assert created_cat["name"] == "Financial"

    updated = risk_api.update_risk_category(
        created_cat["id"],
        RiskCategoryUpdate(description="Updated desc"),
        db_session,
        current_user,
    )
    assert updated["description"] == "Updated desc"

    entry = await risk_api.create_risk_entry(
        RiskEntryCreate(
            category_id=category.id,
            name="KYC gaps",
            description="Missing KYC docs",
            inherent_risk_level="high",
            residual_risk_level="medium",
            likelihood="likely",
            impact="major",
            mitigation_status="in_progress",
            control_owner="compliance",
        ),
        db_session,
        current_user,
    )
    assert entry["name"] == "KYC gaps"

    listing = risk_api.list_risk_entries(
        category_id=category.id,
        inherent_risk_level=None,
        residual_risk_level=None,
        mitigation_status=None,
        q=None,
        skip=0,
        limit=50,
        db=db_session,
        _=None,
    )
    assert listing["total"] >= 1

    fetched = risk_api.get_risk_entry(entry["id"], db_session, None)
    assert fetched["risk_id"]

    updated_entry = risk_api.update_risk_entry(
        entry["id"],
        RiskEntryUpdate(mitigation_status="implemented", metadata={"source": "test"}),
        db_session,
        current_user,
    )
    assert updated_entry["mitigation_status"] == "implemented"

    # Link obligation to risk
    doc = LegalDocument(
        celex="32024R0001",
        title="Compliance obligations",
        jurisdiction="EU",
    )
    obligation = RegulatoryObligation(
        obligation_id="OBL-100",
        document=doc,
        obligation_text="Monitor transactions.",
        status="approved",
    )
    db_session.add_all([doc, obligation])
    db_session.commit()

    link = await risk_api.link_obligation_to_risk(
        entry["id"],
        ObligationRiskLinkCreate(obligation_id=obligation.id),
        db_session,
        current_user,
    )
    assert link["obligation_id"] == obligation.id

    links = risk_api.list_risk_entry_obligations(entry["id"], db_session, None)
    assert links["items"]

    risk_map = risk_api.get_risk_map(db_session, None)
    assert risk_map["total_entries"] >= 1

    heatmap = risk_api.get_risk_heatmap(db_session, None)
    assert heatmap["total_risks"] >= 1

    deletion = risk_api.delete_obligation_risk_link(link["id"], db_session, current_user)
    assert deletion["message"] == "Link removed"

    delete_entry = risk_api.delete_risk_entry(entry["id"], db_session, current_user)
    assert delete_entry["message"] == "Risk entry deleted"

    # delete risk category (no children or entries)
    delete_cat = risk_api.delete_risk_category(created_cat["id"], db_session, current_user)
    assert delete_cat["message"] == "Category deleted"

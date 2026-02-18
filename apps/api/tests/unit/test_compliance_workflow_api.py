import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from src.api import compliance_workflow as workflow_api
from src.auth.dependencies import CurrentUser
from src.models.compliance_workflow import PolicyDocument, RegulatoryObligation
from src.models.models import LegalDocument
from src.models.transaction_models import MonitoringRule
from src.schemas.compliance_workflow_schemas import (
    PolicyCreate,
    PolicyUpdate,
    PolicySectionCreate,
    PolicySectionUpdate,
    InternalRuleCreate,
    InternalRuleUpdate,
    InternalRuleMappingCreate,
)


@pytest.mark.unit
def test_compliance_workflow_endpoints(db_session):
    creator = CurrentUser("user-1", "maker@example.com", "admin")
    approver = CurrentUser("user-2", "checker@example.com", "admin")

    doc = LegalDocument(
        celex="32024R9990",
        title="Compliance doc",
        jurisdiction="EU",
    )
    db_session.add(doc)
    db_session.commit()

    obligation = RegulatoryObligation(
        obligation_id="OBL-WF",
        document=doc,
        obligation_text="Workflow obligation",
        status="draft",
        created_by=creator.email,
    )
    db_session.add(obligation)
    db_session.commit()

    policy = workflow_api.create_policy(
        PolicyCreate(name="Workflow Policy", owner="compliance"),
        db_session,
        creator,
    )
    assert policy["name"] == "Workflow Policy"

    listing = workflow_api.list_policies(None, None, 0, 50, db_session, creator)
    assert listing["total"] >= 1

    fetched = workflow_api.get_policy(policy["id"], db_session, creator)
    assert fetched["policy_id"]
    fetched_by_business_id = workflow_api.get_policy(policy["policy_id"], db_session, creator)
    assert fetched_by_business_id["id"] == policy["id"]

    with pytest.raises(HTTPException) as exc_info:
        workflow_api.update_policy(
            policy["policy_id"],
            PolicyUpdate(status="approved"),
            db_session,
            creator,
        )
    assert exc_info.value.status_code == 409

    updated = workflow_api.update_policy(
        policy["policy_id"],
        PolicyUpdate(status="approved"),
        db_session,
        approver,
    )
    assert updated["status"] == "approved"

    section = workflow_api.create_policy_section(
        policy["policy_id"],
        PolicySectionCreate(section_ref="1", title="Scope", content="Scope"),
        db_session,
        creator,
    )
    assert section["section_ref"] == "1"

    sections = workflow_api.list_policy_sections(policy["id"], db_session, creator)
    assert sections["items"]

    updated_section = workflow_api.update_policy_section(
        section["id"],
        PolicySectionUpdate(title="Updated"),
        db_session,
        creator,
    )
    assert updated_section["title"] == "Updated"

    with pytest.raises(HTTPException) as exc_info:
        workflow_api.approve_obligation(
            obligation.obligation_id,
            {"reviewer_notes": "self approval attempt"},
            db_session,
            creator,
        )
    assert exc_info.value.status_code == 409

    approved_obligation = workflow_api.approve_obligation(
        obligation.obligation_id,
        {"reviewer_notes": "approved by checker"},
        db_session,
        approver,
    )
    assert approved_obligation["status"] == "approved"
    assert approved_obligation["approved_by"] == approver.email

    internal_rule = workflow_api.create_internal_rule(
        obligation.obligation_id,
        InternalRuleCreate(
            name="Internal Rule",
            description="Desc",
            policy_section_id=section["id"],
        ),
        db_session,
        creator,
    )
    assert internal_rule["name"] == "Internal Rule"

    updated_rule = workflow_api.update_internal_rule(
        internal_rule["internal_rule_id"],
        InternalRuleUpdate(status="approved"),
        db_session,
        approver,
    )
    assert updated_rule["status"] == "approved"

    # Create monitoring rule for mapping
    mon_rule = MonitoringRule(
        tenant_id="default",
        rule_id="RULE-WF",
        name="Rule WF",
        description="desc",
        category="velocity",
        severity="high",
        conditions={
            "conditions": [{"field": "amount", "operator": ">", "value": 100}],
            "logic": "AND",
        },
        thresholds=None,
    )
    db_session.add(mon_rule)
    db_session.commit()

    mapping = workflow_api.create_internal_rule_mapping(
        internal_rule["id"],
        InternalRuleMappingCreate(monitoring_rule_rule_id=mon_rule.rule_id),
        db_session,
        creator,
    )
    assert mapping["monitoring_rule"]["rule_id"] == mon_rule.rule_id

    rules = workflow_api.list_internal_rules(obligation.id, db_session, creator)
    assert rules["items"]

    mappings = workflow_api.list_internal_rule_mappings(
        internal_rule["internal_rule_id"], db_session, creator
    )
    assert mappings["items"]

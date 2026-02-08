import pytest
from datetime import datetime, timezone

from src.api import compliance_workflow as workflow_api
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
    )
    db_session.add(obligation)
    db_session.commit()

    policy = workflow_api.create_policy(
        PolicyCreate(name="Workflow Policy", owner="compliance"),
        db_session,
        None,
    )
    assert policy["name"] == "Workflow Policy"

    listing = workflow_api.list_policies(None, None, 0, 50, db_session, None)
    assert listing["total"] >= 1

    fetched = workflow_api.get_policy(policy["id"], db_session, None)
    assert fetched["policy_id"]

    updated = workflow_api.update_policy(
        policy["id"],
        PolicyUpdate(status="approved"),
        db_session,
        None,
    )
    assert updated["status"] == "approved"

    section = workflow_api.create_policy_section(
        policy["id"],
        PolicySectionCreate(section_ref="1", title="Scope", content="Scope"),
        db_session,
        None,
    )
    assert section["section_ref"] == "1"

    sections = workflow_api.list_policy_sections(policy["id"], db_session, None)
    assert sections["items"]

    updated_section = workflow_api.update_policy_section(
        section["id"],
        PolicySectionUpdate(title="Updated"),
        db_session,
        None,
    )
    assert updated_section["title"] == "Updated"

    internal_rule = workflow_api.create_internal_rule(
        obligation.id,
        InternalRuleCreate(
            name="Internal Rule",
            description="Desc",
            policy_section_id=section["id"],
        ),
        db_session,
        None,
    )
    assert internal_rule["name"] == "Internal Rule"

    updated_rule = workflow_api.update_internal_rule(
        internal_rule["id"],
        InternalRuleUpdate(status="approved"),
        db_session,
        None,
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
        None,
    )
    assert mapping["monitoring_rule"]["rule_id"] == mon_rule.rule_id

    rules = workflow_api.list_internal_rules(obligation.id, db_session, None)
    assert rules["items"]

    mappings = workflow_api.list_internal_rule_mappings(internal_rule["id"], db_session, None)
    assert mappings["items"]

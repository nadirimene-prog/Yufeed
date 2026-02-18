from src.models.compliance_workflow import (
    InternalRule,
    InternalRuleMapping,
    ObligationPolicyMapping,
    PolicyDocument,
    RegulatoryObligation,
    TenantObligationApplicability,
)
from src.models.models import LegalDocument
from src.models.transaction_models import MonitoringRule


def _seed_traceability_fixture(db_session):
    regulation = LegalDocument(
        celex="CELEX-TM-001",
        title="Traceability Test Regulation",
        type="regulation",
    )
    db_session.add(regulation)
    db_session.flush()

    covered_obligation = RegulatoryObligation(
        obligation_id="OBL-TM-001",
        doc_id=regulation.id,
        celex=regulation.celex,
        article_ref="Art. 1",
        obligation_text="Covered obligation",
        status="approved",
    )
    gap_obligation = RegulatoryObligation(
        obligation_id="OBL-TM-002",
        doc_id=regulation.id,
        celex=regulation.celex,
        article_ref="Art. 2",
        obligation_text="Uncovered obligation",
        status="approved",
    )
    db_session.add_all([covered_obligation, gap_obligation])
    db_session.flush()

    db_session.add_all(
        [
            TenantObligationApplicability(
                tenant_id="default",
                obligation_id=covered_obligation.id,
                applicability="applicable",
            ),
            TenantObligationApplicability(
                tenant_id="default",
                obligation_id=gap_obligation.id,
                applicability="applicable",
            ),
        ]
    )

    policy = PolicyDocument(
        policy_id="POL-TM-001",
        tenant_id="default",
        name="Traceability Policy",
        status="approved",
    )
    db_session.add(policy)
    db_session.flush()

    db_session.add(
        ObligationPolicyMapping(
            obligation_id=covered_obligation.id,
            policy_id=policy.id,
            mapped_by="tester",
            mapping_confidence=0.95,
        )
    )

    internal_rule = InternalRule(
        internal_rule_id="IR-TM-001",
        tenant_id="default",
        obligation_id=covered_obligation.id,
        name="Traceability Internal Rule",
        status="implemented",
    )
    db_session.add(internal_rule)
    db_session.flush()

    monitoring_rule = MonitoringRule(
        tenant_id="default",
        rule_id="MR-TM-001",
        name="Traceability Monitoring Rule",
        conditions={"logic": "AND", "conditions": []},
        enabled=True,
    )
    db_session.add(monitoring_rule)
    db_session.flush()

    db_session.add(
        InternalRuleMapping(
            internal_rule_id=internal_rule.id,
            tenant_id="default",
            monitoring_rule_id=monitoring_rule.id,
            mapping_type="transaction_monitoring",
        )
    )
    db_session.commit()

    return {
        "regulation_id": regulation.id,
        "covered_obligation_id": covered_obligation.obligation_id,
        "gap_obligation_id": gap_obligation.obligation_id,
    }


def test_traceability_matrix_and_coverage(client, db_session, admin_headers):
    seeded = _seed_traceability_fixture(db_session)

    response = client.get("/api/traceability-matrix/default", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()

    assert payload["tenant_id"] == "default"
    assert payload["coverage"]["total_obligations"] == 2
    assert payload["coverage"]["levels"]["policy"]["covered"] == 1
    assert payload["coverage"]["levels"]["internal_rule"]["covered"] == 1
    assert payload["coverage"]["levels"]["monitoring_rule"]["covered"] == 1

    items = payload["matrix"]["items"]
    assert len(items) == 2
    covered_item = next(
        item
        for item in items
        if item["obligation"]["obligation_id"] == seeded["covered_obligation_id"]
    )
    gap_item = next(
        item for item in items if item["obligation"]["obligation_id"] == seeded["gap_obligation_id"]
    )
    assert covered_item["coverage"]["has_monitoring_rule"] is True
    assert gap_item["coverage"]["has_policy"] is False


def test_traceability_gaps_and_regulation_view(client, db_session, admin_headers):
    seeded = _seed_traceability_fixture(db_session)

    gaps_response = client.get("/api/traceability-matrix/default/gaps", headers=admin_headers)
    assert gaps_response.status_code == 200
    gaps_payload = gaps_response.json()

    assert gaps_payload["summary"]["obligations_without_policy"] == 1
    assert gaps_payload["summary"]["obligations_without_internal_rule"] == 1
    assert gaps_payload["summary"]["obligations_without_monitoring_rule"] == 1
    assert any(
        obligation["obligation_id"] == seeded["gap_obligation_id"]
        for obligation in gaps_payload["gaps"]["obligations_without_policy"]
    )

    regulation_response = client.get(
        f"/api/traceability-matrix/default/regulation/{seeded['regulation_id']}",
        headers=admin_headers,
    )
    assert regulation_response.status_code == 200
    regulation_payload = regulation_response.json()
    assert regulation_payload["coverage"]["total_obligations"] == 2
    assert regulation_payload["coverage"]["levels"]["policy"]["covered"] == 1


def test_traceability_matrix_forbidden_cross_tenant(client, db_session, admin_headers):
    _seed_traceability_fixture(db_session)
    response = client.get("/api/traceability-matrix/another-tenant", headers=admin_headers)
    assert response.status_code == 403

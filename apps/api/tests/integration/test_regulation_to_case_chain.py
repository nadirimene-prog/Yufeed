"""Integration test for full regulation-to-case traceability chain."""

from datetime import datetime, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.compliance_workflow import RegulatoryObligation
from src.models.finding_models import Finding
from src.models.models import LegalDocument
from src.models.transaction_models import Case


@pytest.mark.integration
def test_regulation_to_case_full_chain(
    client: TestClient,
    db_session: Session,
    admin_headers: dict,
    monkeypatch,
):
    monkeypatch.setenv("ENVIRONMENT", "test")

    suffix = uuid.uuid4().hex[:8].upper()
    celex = f"E2E-REG-{suffix}"
    obligation_public_id = f"OBL-E2E-{suffix}"
    user_id = f"user_chain_{suffix.lower()}"
    transaction_id = f"txn_chain_{suffix.lower()}"

    # Seed regulation + obligation.
    regulation = LegalDocument(
        celex=celex,
        title=f"E2E Regulation {suffix}",
        type="regulation",
        source_system="eur-lex",
        jurisdiction="EU",
    )
    db_session.add(regulation)
    db_session.flush()

    obligation = RegulatoryObligation(
        obligation_id=obligation_public_id,
        doc_id=regulation.id,
        celex=celex,
        article_ref="Art. 12",
        obligation_text="Monitor and flag all transactions above 10000 EUR.",
        status="draft",
        created_by="obligation.author@example.com",
    )
    db_session.add(obligation)
    db_session.commit()
    db_session.refresh(obligation)

    # Create tenant policy.
    create_policy_resp = client.post(
        "/api/policies",
        headers=admin_headers,
        json={
            "name": f"E2E Monitoring Policy {suffix}",
            "owner": "compliance@example.com",
            "status": "draft",
            "content": "Policy content for high-value transaction monitoring.",
        },
    )
    assert create_policy_resp.status_code in {200, 201}
    policy = create_policy_resp.json()

    # Approve obligation and force link to policy, creating an internal rule.
    approve_resp = client.patch(
        f"/api/obligations/{obligation.id}/approve",
        headers=admin_headers,
        json={
            "status": "approved",
            "note": "Approved and mapped for production monitoring.",
            "linked_policy_id": policy["id"],
            "create_internal_rule": True,
            "internal_rule_name": f"E2E internal rule {suffix}",
            "internal_rule_description": "Escalate high-value transaction breaches.",
        },
    )
    assert approve_resp.status_code == 200
    approved_obligation = approve_resp.json()

    created_internal = approved_obligation.get("created_internal_rule") or {}
    internal_rule_public_id = created_internal.get("internal_rule_id")
    if not internal_rule_public_id:
        rules_resp = client.get(
            f"/api/compliance/obligations/{obligation_public_id}/internal-rules",
            headers=admin_headers,
        )
        assert rules_resp.status_code == 200
        rules = rules_resp.json()["items"]
        assert rules
        internal_rule_public_id = rules[0]["internal_rule_id"]

    # Create monitoring rule and map internal rule -> monitoring rule.
    create_monitoring_rule_resp = client.post(
        "/api/monitoring-rules",
        headers=admin_headers,
        json={
            "name": f"E2E high value rule {suffix}",
            "description": "Trigger when amount > 10000 EUR",
            "category": "high_value",
            "severity": "high",
            "conditions": {
                "logic": "AND",
                "conditions": [
                    {
                        "field": "amount",
                        "operator": ">",
                        "value": 10000,
                    }
                ],
            },
            "regulatory_source_id": regulation.id,
            "regulation_article": "Art. 12",
            "regulatory_requirement": "Flag transactions above threshold.",
            "enabled": True,
        },
    )
    assert create_monitoring_rule_resp.status_code == 201
    monitoring_rule = create_monitoring_rule_resp.json()

    mapping_resp = client.post(
        f"/api/compliance/internal-rules/{internal_rule_public_id}/mappings",
        headers=admin_headers,
        json={
            "monitoring_rule_rule_id": monitoring_rule["rule_id"],
            "mapping_type": "transaction_monitoring",
        },
    )
    assert mapping_resp.status_code == 201

    # Validate traceability matrix coverage for this obligation.
    matrix_resp = client.get(
        f"/api/traceability-matrix/default?obligation_id={obligation_public_id}",
        headers=admin_headers,
    )
    assert matrix_resp.status_code == 200
    matrix_payload = matrix_resp.json()
    assert matrix_payload["coverage"]["levels"]["policy"]["covered"] >= 1
    assert matrix_payload["coverage"]["levels"]["internal_rule"]["covered"] >= 1
    assert matrix_payload["coverage"]["levels"]["monitoring_rule"]["covered"] >= 1

    target_item = next(
        (
            item
            for item in matrix_payload["matrix"]["items"]
            if item["obligation"]["obligation_id"] == obligation_public_id
        ),
        None,
    )
    assert target_item is not None
    assert target_item["coverage"]["has_policy"] is True
    assert target_item["coverage"]["has_internal_rule"] is True
    assert target_item["coverage"]["has_monitoring_rule"] is True
    assert any(
        rule["rule_id"] == monitoring_rule["rule_id"] for rule in target_item["monitoring_rules"]
    )

    gaps_resp = client.get("/api/traceability-matrix/default/gaps", headers=admin_headers)
    assert gaps_resp.status_code == 200
    gaps = gaps_resp.json()["gaps"]
    assert all(
        row["obligation_id"] != obligation_public_id for row in gaps["obligations_without_policy"]
    )
    assert all(
        row["obligation_id"] != obligation_public_id
        for row in gaps["obligations_without_internal_rule"]
    )
    assert all(
        row["obligation_id"] != obligation_public_id
        for row in gaps["obligations_without_monitoring_rule"]
    )

    # Ingest transaction, produce alert and finding, then escalate to case.
    ingest_resp = client.post(
        "/api/transactions",
        headers=admin_headers,
        json={
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": 15000.00,
            "currency": "EUR",
            "transaction_type": "transfer",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "country_code": "FR",
        },
    )
    assert ingest_resp.status_code == 201

    alerts_resp = client.get(f"/api/alerts?user_id={user_id}", headers=admin_headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert alerts

    alert = next(
        (
            item
            for item in alerts
            if (item.get("evidence") or {}).get("rule_id") == monitoring_rule["rule_id"]
        ),
        None,
    )
    assert alert is not None

    db_session.expire_all()
    finding_row = next(
        (
            row
            for row in db_session.query(Finding)
            .filter(
                Finding.tenant_id == "default",
                Finding.finding_type == "TX_ALERT",
            )
            .all()
            if (row.source_refs_json or {}).get("rule_id") == monitoring_rule["rule_id"]
            and (row.source_refs_json or {}).get("transaction_id") == transaction_id
        ),
        None,
    )
    assert finding_row is not None

    escalate_resp = client.post(
        f"/api/findings/{finding_row.id}/escalate",
        headers=admin_headers,
        json={
            "title": f"E2E Case {suffix}",
            "description": "Escalated from finding in E2E chain test.",
            "priority": "high",
        },
    )
    assert escalate_resp.status_code == 200
    case = escalate_resp.json()
    assert case["case_id"]

    case_resp = client.get(f"/api/cases/{case['case_id']}", headers=admin_headers)
    assert case_resp.status_code == 200
    assert case_resp.json()["status"] == "open"

    db_session.expire_all()
    db_case = db_session.query(Case).filter(Case.case_id == case["case_id"]).first()
    assert db_case is not None
    assert any(linked_finding.id == finding_row.id for linked_finding in db_case.findings)

    db_finding = db_session.query(Finding).filter(Finding.id == finding_row.id).first()
    assert db_finding is not None
    assert db_finding.status == "escalated"

"""Regression tests for findings API serialization fields."""

import uuid


def test_findings_http_exposes_source_refs_and_explainability(client, admin_headers):
    fingerprint = f"default:TX_ALERT:{uuid.uuid4().hex[:12]}"
    create_resp = client.post(
        "/api/findings",
        headers=admin_headers,
        json={
            "finding_type": "TX_ALERT",
            "fingerprint": fingerprint,
            "severity": "high",
            "title": "Serialization regression",
            "source_refs": {
                "alert_id": "ALT-TEST-001",
                "transaction_id": "txn-serialization-001",
                "rule_id": "RULE-TEST-001",
            },
            "explainability": {
                "matched_rules": {"RULE-TEST-001": "High value transfer"},
                "evidence": {"amount": 15000},
            },
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["source_refs"]["alert_id"] == "ALT-TEST-001"
    assert created["source_refs"]["rule_id"] == "RULE-TEST-001"
    assert created["explainability"]["evidence"]["amount"] == 15000

    get_resp = client.get(f"/api/findings/{created['id']}", headers=admin_headers)
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["source_refs"]["transaction_id"] == "txn-serialization-001"
    assert fetched["explainability"]["matched_rules"]["RULE-TEST-001"] == "High value transfer"

from fastapi.testclient import TestClient


def test_audit_event_and_decision_flow(client: TestClient, admin_headers: dict):
    event_res = client.post(
        "/api/audit/events",
        json={
            "event_type": "txn_fiat",
            "entity_type": "transaction",
            "entity_id": "TX-TEST-1",
            "payload": {"amount": 1000, "currency": "EUR"},
        },
        headers=admin_headers,
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["event_id"]

    decision_res = client.post(
        "/api/audit/decisions",
        json={
            "decision": "alert",
            "event_id": event_id,
            "reason_codes": ["RULE-001"],
            "rule_version": "1",
        },
        headers=admin_headers,
    )
    assert decision_res.status_code == 201
    decision_id = decision_res.json()["decision_id"]

    get_event = client.get(f"/api/audit/events/{event_id}", headers=admin_headers)
    assert get_event.status_code == 200
    assert get_event.json()["event_id"] == event_id

    get_decision = client.get(f"/api/audit/decisions/{decision_id}", headers=admin_headers)
    assert get_decision.status_code == 200
    assert get_decision.json()["decision_id"] == decision_id

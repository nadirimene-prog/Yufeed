import pytest


@pytest.mark.unit
def test_rules_alias_uses_monitoring_rules(client, auth_headers):
    payload = {
        "rule_id": "RULE-LEGACY-001",
        "name": "Legacy Rule Alias",
        "description": "Legacy create via /api/rules",
        "category": "velocity",
        "severity": "medium",
        "priority": 2,
        "enabled": True,
        "is_template": False,
        "conditions_json": {
            "logic": "AND",
            "conditions": [
                {"field": "amount", "operator": ">", "value": 1000},
            ],
        },
        "aggregation_json": {
            "window_size": "24h",
            "metric": "sum",
            "field": "amount",
        },
    }

    create_resp = client.post("/api/rules", json=payload, headers=auth_headers)
    assert create_resp.status_code == 200
    assert create_resp.headers.get("X-Deprecated") == "true"
    created = create_resp.json()
    rule_id = created["rule_id"]

    get_resp = client.get(f"/api/rules/{rule_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.headers.get("X-Deprecated") == "true"

    list_resp = client.get("/api/rules", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.headers.get("X-Deprecated") == "true"

    canonical_resp = client.get("/api/monitoring-rules", headers=auth_headers)
    assert canonical_resp.status_code == 200
    rules = canonical_resp.json()
    assert any(rule["rule_id"] == rule_id for rule in rules)

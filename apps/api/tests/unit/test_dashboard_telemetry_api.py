import pytest


@pytest.mark.unit
def test_dashboard_telemetry_ingests_batch(client, auth_headers):
    response = client.post(
        "/api/dashboard/telemetry/events",
        json={
            "events": [
                {
                    "event": "dashboard_filter_apply",
                    "payload": {"source": "queue_controls", "keys": ["search", "page"]},
                    "at": "2026-02-26T12:00:00Z",
                },
                {
                    "event": "dashboard_shortcut_used",
                    "payload": {"shortcut": "g q"},
                    "at": "2026-02-26T12:00:01Z",
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["accepted"] == 2
    assert body["dropped"] == 0


@pytest.mark.unit
def test_dashboard_telemetry_rejects_empty_batch(client, auth_headers):
    response = client.post(
        "/api/dashboard/telemetry/events",
        json={"events": []},
        headers=auth_headers,
    )

    assert response.status_code == 422

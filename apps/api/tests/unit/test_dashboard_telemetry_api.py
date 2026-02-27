import pytest
from src.audit.models import EventRecord


@pytest.mark.unit
def test_dashboard_telemetry_ingests_batch(client, auth_headers, db_session):
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
                {
                    "event": "dashboard_ui_timing",
                    "payload": {
                        "metric": "queue_render_complete",
                        "success": True,
                        "latency_ms": 84,
                    },
                    "at": "2026-02-26T12:00:02Z",
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["accepted"] == 3
    assert body["dropped"] == 0
    persisted = (
        db_session.query(EventRecord)
        .filter(
            EventRecord.event_type.in_(
                [
                    "dashboard.telemetry.dashboard_filter_apply",
                    "dashboard.telemetry.dashboard_shortcut_used",
                    "dashboard.telemetry.dashboard_ui_timing",
                ]
            )
        )
        .all()
    )
    assert len(persisted) >= 3
    assert any(
        isinstance(row.payload, dict)
        and row.payload.get("event") == "dashboard_ui_timing"
        and isinstance(row.payload.get("payload"), dict)
        and row.payload["payload"].get("metric") == "queue_render_complete"
        for row in persisted
    )


@pytest.mark.unit
def test_dashboard_telemetry_rejects_empty_batch(client, auth_headers):
    response = client.post(
        "/api/dashboard/telemetry/events",
        json={"events": []},
        headers=auth_headers,
    )

    assert response.status_code == 422

import pytest

from src.api import alerts as alerts_api
from src.schemas.transaction_schemas import AlertCreate
from src.tenancy.context import set_current_tenant, clear_current_tenant


def _stub_prediction():
    return {
        "prediction": "unknown",
        "confidence": 0.5,
        "recommendation": "manual_review",
        "model_version": "test",
    }


@pytest.mark.unit
def test_create_alert_uses_finding_service(db_session, monkeypatch):
    calls = []

    class StubFindingService:
        def __init__(self, db):
            self.db = db

        def create_or_update_finding(self, **kwargs):
            calls.append(kwargs)
            return None, True

    monkeypatch.setattr(alerts_api, "FindingService", StubFindingService)
    monkeypatch.setattr(
        alerts_api.alert_triage_model, "predict", lambda db, alert: _stub_prediction()
    )

    set_current_tenant("default")
    try:
        created = alerts_api.create_alert(
            AlertCreate(
                alert_type="test_alert",
                severity="medium",
                user_id="user-1",
                description="Test finding upsert",
            ),
            db_session,
        )
    finally:
        clear_current_tenant()

    assert created.alert_id.startswith("ALT-")
    assert calls
    assert calls[0]["finding_type"] == "TX_ALERT"
    assert calls[0]["source_refs"]["alert_id"] == created.alert_id


@pytest.mark.unit
def test_create_alert_handles_non_numeric_ml_confidence(db_session, monkeypatch):
    class StubFindingService:
        def __init__(self, db):
            self.db = db

        def create_or_update_finding(self, **kwargs):
            return None, True

    monkeypatch.setattr(alerts_api, "FindingService", StubFindingService)
    monkeypatch.setattr(
        alerts_api.alert_triage_model,
        "predict",
        lambda db, alert: {
            "prediction": "unknown",
            "confidence": "low",
            "true_positive_probability": 0.5,
            "false_positive_probability": 0.5,
            "recommendation": "manual_review",
            "model_version": "test",
        },
    )

    set_current_tenant("default")
    try:
        created = alerts_api.create_alert(
            AlertCreate(
                alert_type="test_alert",
                severity="medium",
                user_id="user-ml-fallback",
                description="Non-numeric confidence should not fail",
            ),
            db_session,
        )
    finally:
        clear_current_tenant()

    assert created.ml_prediction == "unknown"
    assert float(created.ml_confidence) == 0.5


@pytest.mark.unit
def test_create_alert_continues_when_finding_service_fails(db_session, monkeypatch):
    class FailingFindingService:
        def __init__(self, db):
            self.db = db

        def create_or_update_finding(self, **kwargs):
            raise RuntimeError("finding failure")

    monkeypatch.setattr(alerts_api, "FindingService", FailingFindingService)
    monkeypatch.setattr(
        alerts_api.alert_triage_model, "predict", lambda db, alert: _stub_prediction()
    )

    set_current_tenant("default")
    try:
        created = alerts_api.create_alert(
            AlertCreate(
                alert_type="test_alert",
                severity="low",
                user_id="user-2",
                description="Should still create alert",
            ),
            db_session,
        )
    finally:
        clear_current_tenant()

    assert created.alert_id.startswith("ALT-")

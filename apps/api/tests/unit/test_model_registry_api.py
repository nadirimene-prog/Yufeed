import pytest
from datetime import datetime, timezone

from src.api import model_registry as model_api
from src.schemas.model_registry import ModelCreate, ModelVersionCreate, DriftReportCreate


@pytest.mark.unit
def test_model_registry_flow(db_session):
    model = model_api.create_model(
        ModelCreate(
            model_id="risk-model",
            name="Risk Model",
            description="Test model",
            model_type="ml",
            owner="ml-team",
            status="active",
        ),
        db_session,
        None,
    )
    assert model.model_id == "risk-model"

    models = model_api.list_models(None, db_session, None)
    assert models

    version = model_api.create_version(
        model.model_id,
        ModelVersionCreate(version="1.0", status="staging", metrics={"auc": 0.9}),
        db_session,
        None,
    )
    assert version.version == "1.0"

    versions = model_api.list_versions(model.model_id, db_session, None)
    assert versions

    promoted = model_api.promote_version(model.model_id, version.id, db_session, None)
    assert promoted.status == "production"

    drift = model_api.record_drift(
        model.model_id,
        version.id,
        DriftReportCreate(drift_score=0.1, status="ok", metrics={"psi": 0.02}),
        db_session,
        None,
    )
    assert drift.status == "ok"

    reports = model_api.list_drift_reports(model.model_id, version.id, db_session, None)
    assert reports

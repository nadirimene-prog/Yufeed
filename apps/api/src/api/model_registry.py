from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.model_registry import ModelRegistry, ModelVersion, ModelDriftReport
from src.schemas.model_registry import (
    ModelCreate,
    ModelResponse,
    ModelVersionCreate,
    ModelVersionResponse,
    DriftReportCreate,
    DriftReportResponse,
)

router = APIRouter(prefix="/api/models", tags=["model-registry"])


@router.post("/", response_model=ModelResponse, status_code=201)
def create_model(
    model: ModelCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"])),
):
    existing = db.query(ModelRegistry).filter(ModelRegistry.model_id == model.model_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Model already exists")

    db_model = ModelRegistry(**model.dict())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.get("/", response_model=List[ModelResponse])
def list_models(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"])),
):
    query = db.query(ModelRegistry)
    if status:
        query = query.filter(ModelRegistry.status == status)
    return query.order_by(ModelRegistry.created_at.desc()).all()


@router.post("/{model_id}/versions", response_model=ModelVersionResponse, status_code=201)
def create_version(
    model_id: str,
    version: ModelVersionCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"])),
):
    model = db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    db_version = ModelVersion(model_id=model.id, **version.dict())
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version


@router.get("/{model_id}/versions", response_model=List[ModelVersionResponse])
def list_versions(
    model_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"])),
):
    model = db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return (
        db.query(ModelVersion)
        .filter(ModelVersion.model_id == model.id)
        .order_by(ModelVersion.created_at.desc())
        .all()
    )


@router.post("/{model_id}/versions/{version_id}/promote", response_model=ModelVersionResponse)
def promote_version(
    model_id: str,
    version_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    model = db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == version_id, ModelVersion.model_id == model.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Model version not found")

    version.status = "production"
    version.promoted_at = utc_now()
    db.commit()
    db.refresh(version)
    return version


@router.post(
    "/{model_id}/versions/{version_id}/drift", response_model=DriftReportResponse, status_code=201
)
def record_drift(
    model_id: str,
    version_id: int,
    report: DriftReportCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"])),
):
    model = db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == version_id, ModelVersion.model_id == model.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Model version not found")

    drift = ModelDriftReport(
        model_version_id=version.id,
        drift_score=report.drift_score,
        status=report.status,
        window_start=report.window_start,
        window_end=report.window_end,
        metrics=report.metrics,
    )
    db.add(drift)
    db.commit()
    db.refresh(drift)
    return drift


@router.get("/{model_id}/versions/{version_id}/drift", response_model=List[DriftReportResponse])
def list_drift_reports(
    model_id: str,
    version_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "user"])),
):
    model = db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == version_id, ModelVersion.model_id == model.id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Model version not found")

    return (
        db.query(ModelDriftReport)
        .filter(ModelDriftReport.model_version_id == version.id)
        .order_by(ModelDriftReport.observed_at.desc())
        .all()
    )

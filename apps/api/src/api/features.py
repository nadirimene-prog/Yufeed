"""
Feature Store API Endpoints
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.auth.dependencies import require_any_role, CurrentUser
from src.database import get_db
from src.services.feature_store import FeatureStoreService


router = APIRouter(prefix="/api/features", tags=["features"])


class FeaturePayload(BaseModel):
    value: Any
    feature_type: Optional[str] = Field(None, max_length=50)
    calculated_at: Optional[datetime] = None
    version: int = 1


class FeatureSetRequest(BaseModel):
    entity_type: str = Field(..., max_length=50)
    entity_id: str = Field(..., max_length=255)
    features: Dict[str, FeaturePayload]


class FeatureResponse(BaseModel):
    feature_name: str
    value: Any
    feature_type: Optional[str]
    calculated_at: str
    version: int


class FeatureSetResponse(BaseModel):
    entity_type: str
    entity_id: str
    features: Dict[str, FeatureResponse]


@router.post("/set", response_model=FeatureSetResponse)
def set_features(
    request: FeatureSetRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    service = FeatureStoreService(db)
    payloads = {
        name: {
            "value": feature.value,
            "feature_type": feature.feature_type,
            "calculated_at": feature.calculated_at,
            "version": feature.version,
        }
        for name, feature in request.features.items()
    }
    records = service.upsert_features(request.entity_type, request.entity_id, payloads)
    db.commit()

    features = {
        name: FeatureResponse(
            feature_name=name,
            value=record.feature_value,
            feature_type=record.feature_type,
            calculated_at=record.calculated_at.isoformat(),
            version=record.version,
        )
        for name, record in records.items()
    }
    return FeatureSetResponse(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        features=features,
    )


@router.get("/{entity_type}/{entity_id}", response_model=FeatureSetResponse)
def get_features(
    entity_type: str,
    entity_id: str,
    names: Optional[str] = Query(None, description="Comma-separated feature names"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    service = FeatureStoreService(db)
    name_list = [name.strip() for name in names.split(",") if name.strip()] if names else None
    features = service.get_features(entity_type, entity_id, name_list)

    return FeatureSetResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        features={
            name: FeatureResponse(
                feature_name=name,
                value=data.get("value"),
                feature_type=data.get("feature_type"),
                calculated_at=data.get("calculated_at"),
                version=data.get("version", 1),
            )
            for name, data in features.items()
        },
    )


@router.get("/{entity_type}/{entity_id}/{feature_name}", response_model=FeatureResponse)
def get_feature(
    entity_type: str,
    entity_id: str,
    feature_name: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    service = FeatureStoreService(db)
    feature = service.get_feature(entity_type, entity_id, feature_name)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    return FeatureResponse(
        feature_name=feature_name,
        value=feature.get("value"),
        feature_type=feature.get("feature_type"),
        calculated_at=feature.get("calculated_at"),
        version=feature.get("version", 1),
    )


@router.delete("/{entity_type}/{entity_id}/{feature_name}")
def delete_feature(
    entity_type: str,
    entity_id: str,
    feature_name: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    service = FeatureStoreService(db)
    service.delete_feature(entity_type, entity_id, feature_name)
    return {"status": "deleted"}

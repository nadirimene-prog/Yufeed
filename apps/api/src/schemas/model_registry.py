from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    model_id: str = Field(..., max_length=255)
    name: str
    description: Optional[str] = None
    model_type: str = Field("ml", max_length=100)
    owner: Optional[str] = None
    status: str = Field("active", max_length=50)


class ModelResponse(ModelCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelVersionCreate(BaseModel):
    version: str
    status: str = Field("staging", max_length=50)
    artifact_uri: Optional[str] = None
    feature_set_hash: Optional[str] = None
    training_window: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class ModelVersionResponse(ModelVersionCreate):
    id: int
    model_id: int
    created_at: datetime
    promoted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DriftReportCreate(BaseModel):
    drift_score: Optional[float] = None
    status: str = Field("ok", max_length=50)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    metrics: Optional[Dict[str, Any]] = None


class DriftReportResponse(DriftReportCreate):
    id: int
    model_version_id: int
    observed_at: datetime

    class Config:
        from_attributes = True

"""Pydantic schemas for Evidence Packs."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class EvidencePackCreateRequest(BaseModel):
    """Request to generate an evidence pack for a case."""

    format: str = Field("json", description="Output format: json or pdf")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("json", "pdf"):
            raise ValueError("format must be 'json' or 'pdf'")
        return v


class EvidencePackResponse(BaseModel):
    """Evidence pack metadata (without the full snapshot)."""

    id: int
    pack_id: str
    case_id: int
    schema_version: str
    version: int
    format: str
    integrity_hash: str
    storage_ref: Optional[str] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class EvidencePackDetailResponse(EvidencePackResponse):
    """Evidence pack with the full snapshot included."""

    snapshot: Optional[Dict[str, Any]] = Field(None, alias="snapshot_json")

    class Config:
        from_attributes = True
        populate_by_name = True

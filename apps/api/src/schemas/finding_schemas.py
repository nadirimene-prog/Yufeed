"""Pydantic schemas for Findings (finding-first workbench)."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class FindingBase(BaseModel):
    finding_type: str = Field(..., max_length=50)
    severity: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None
    source_refs: Optional[Dict[str, Any]] = None
    explainability: Optional[Dict[str, Any]] = None
    assigned_to: Optional[str] = Field(None, max_length=255)
    sla_due_at: Optional[datetime] = None


class FindingCreate(FindingBase):
    fingerprint: str = Field(..., max_length=128)


class FindingUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=20)
    assigned_to: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None
    sla_due_at: Optional[datetime] = None


class FindingResponse(FindingBase):
    id: int
    tenant_id: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EscalateToCaseRequest(BaseModel):
    case_type: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, max_length=20)


class CaseLiteResponse(BaseModel):
    id: int
    case_id: str
    status: str
    title: Optional[str] = None

    class Config:
        from_attributes = True

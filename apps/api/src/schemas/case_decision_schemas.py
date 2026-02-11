"""Pydantic schemas for Case Decisions (governance workflow)."""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CaseDecisionCreate(BaseModel):
    """Create a draft decision for a case."""

    disposition: str = Field(..., max_length=50)
    rationale: Optional[str] = None


class CaseDecisionSubmit(BaseModel):
    """Submit a draft decision for approval."""

    rationale: str = Field(..., min_length=10, description="Rationale is required on submit")


class CaseDecisionApprove(BaseModel):
    """Approve a submitted decision (identity comes from auth)."""

    comment: Optional[str] = None


class CaseDecisionReject(BaseModel):
    """Reject a submitted decision."""

    rejection_reason: str = Field(..., min_length=10)


class CaseDecisionResponse(BaseModel):
    """Response schema for a case decision."""

    id: int
    tenant_id: str
    case_id: int
    version: int
    status: str
    disposition: str
    rationale: Optional[str] = None
    created_by: str
    submitted_at: Optional[datetime] = None
    approver_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

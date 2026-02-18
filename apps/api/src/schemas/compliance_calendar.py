"""Compliance calendar schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CalendarEventRead(BaseModel):
    id: int
    tenant_id: str
    event_type: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    regulation_doc_id: Optional[int] = None
    obligation_id: Optional[int] = None
    policy_id: Optional[int] = None
    compliance_profile_id: Optional[int] = None
    status: str
    assigned_to: Optional[str] = None
    priority: str
    reminder_days_before: int
    reminder_count: int
    last_reminder_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CalendarEventListResponse(BaseModel):
    total: int
    items: List[CalendarEventRead] = Field(default_factory=list)


class CalendarSeedRequest(BaseModel):
    include_obligations: bool = True
    include_policy_reviews: bool = True
    include_kyc_reviews: bool = True


class CalendarSeedResponse(BaseModel):
    tenant_id: str
    created: Dict[str, int]
    total_created: int


class CalendarEventStatusUpdate(BaseModel):
    status: str
    assigned_to: Optional[str] = None
    priority: Optional[str] = None


class RegulatoryChangeResponse(BaseModel):
    tenant_id: str
    regulation_doc_id: int
    created_events: int

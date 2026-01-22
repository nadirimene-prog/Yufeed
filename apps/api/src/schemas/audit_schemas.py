"""
Audit/Event/Decision Pydantic Schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class AuditLogResponse(BaseModel):
    audit_id: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    actor_type: Optional[str] = None
    actor_ip: Optional[str] = None
    user_agent: Optional[str] = None
    action: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    event_type: str = Field(..., max_length=100)
    entity_type: Optional[str] = Field(None, max_length=100)
    entity_id: Optional[str] = Field(None, max_length=255)
    source: Optional[str] = Field(None, max_length=100)
    payload: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = Field(None, max_length=64)


class EventResponse(EventCreate):
    event_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class DecisionCreate(BaseModel):
    decision: str = Field(..., max_length=20)
    reason_codes: Optional[List[str]] = None
    rule_version: Optional[str] = Field(None, max_length=50)
    model_version: Optional[str] = Field(None, max_length=50)
    evidence: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = Field(None, max_length=64)
    decision_id: Optional[str] = Field(None, max_length=64)


class DecisionResponse(DecisionCreate):
    decision_id: str
    created_at: datetime

    class Config:
        from_attributes = True

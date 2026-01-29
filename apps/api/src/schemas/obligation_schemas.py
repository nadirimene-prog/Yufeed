from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class ObligationUpdate(BaseModel):
    """Basic obligation status update."""
    status: str = Field(..., min_length=2, max_length=50)
    note: Optional[str] = None


class ObligationApproval(BaseModel):
    """Enhanced approval with policy linking and internal rule creation."""
    status: str = Field(..., min_length=2, max_length=50)
    note: Optional[str] = None
    linked_policy_id: Optional[int] = None
    create_internal_rule: bool = False
    internal_rule_name: Optional[str] = None
    internal_rule_description: Optional[str] = None
    link_risk_entry_ids: Optional[List[int]] = None


class ObligationDocumentSummary(BaseModel):
    id: int
    celex: str
    title: str
    jurisdiction: Optional[str] = None
    source_system: Optional[str] = None
    publication_date: Optional[str] = None
    scope_tags: Optional[List[str]] = None


class ObligationResponse(BaseModel):
    id: int
    obligation_id: str
    status: str
    article_ref: Optional[str] = None
    obligation_text: str
    applicability: Optional[str] = None
    effective_date: Optional[str] = None
    created_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    review_notes: Optional[str] = None
    updated_at: Optional[str] = None
    scope_tags: Optional[List[str]] = None
    tags: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    document: ObligationDocumentSummary

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class ObligationUpdate(BaseModel):
    status: str = Field(..., min_length=2, max_length=50)
    note: Optional[str] = None


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

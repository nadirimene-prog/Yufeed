"""Policy management schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """Schema for creating a new policy document."""

    name: str = Field(..., min_length=1, max_length=255)
    version: Optional[str] = None
    owner: Optional[str] = None
    status: str = Field(default="draft", pattern="^(draft|in_review|approved|active|retired)$")
    language: str = Field(default="en", max_length=10)
    effective_date: Optional[datetime] = None
    source_url: Optional[str] = Field(
        None, max_length=1000, description="External document URL (e.g., Notion)"
    )
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PolicyUpdate(BaseModel):
    """Schema for updating an existing policy document."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    version: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|in_review|approved|active|retired)$")
    language: Optional[str] = Field(None, max_length=10)
    effective_date: Optional[datetime] = None
    source_url: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PolicyApprove(BaseModel):
    """Schema for approving a policy."""

    note: Optional[str] = None


class PolicySectionCreate(BaseModel):
    """Schema for creating a policy section."""

    section_ref: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    status: str = Field(default="draft", pattern="^(draft|in_review|approved|archived)$")
    version: Optional[str] = Field(None, max_length=50)


class PolicySectionUpdate(BaseModel):
    """Schema for updating a policy section."""

    section_ref: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|in_review|approved|archived)$")
    version: Optional[str] = Field(None, max_length=50)


class PolicySectionResponse(BaseModel):
    """Response schema for a policy section."""

    id: int
    policy_id: int
    section_ref: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    status: str
    version: Optional[str] = None
    last_reviewed_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PolicyTemplateResponse(BaseModel):
    """Response schema for a policy template."""

    id: int
    template_id: str
    name: str
    category: str
    version: Optional[str] = None
    owner: Optional[str] = None
    review_frequency_months: Optional[int] = None
    regulatory_basis: Optional[List[str]] = None
    source_url: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PolicyTemplateListResponse(BaseModel):
    """Response schema for paginated policy template list."""

    total: int
    items: List[PolicyTemplateResponse]


class PolicyFromTemplateCreate(BaseModel):
    """Schema for creating a policy from a template with optional overrides."""

    name: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|in_review|approved|active|retired)$")
    language: Optional[str] = Field(None, max_length=10)
    effective_date: Optional[datetime] = None
    source_url: Optional[str] = Field(None, max_length=1000)
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PolicyResponse(BaseModel):
    """Response schema for a policy document."""

    id: int
    policy_id: str
    name: str
    version: Optional[str] = None
    owner: Optional[str] = None
    status: str
    language: str
    effective_date: Optional[str] = None
    last_reviewed_at: Optional[str] = None
    source_url: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: Optional[str] = None
    sections_count: Optional[int] = None
    linked_obligations_count: Optional[int] = None

    class Config:
        from_attributes = True


class PolicyListResponse(BaseModel):
    """Response schema for paginated policy list."""

    total: int
    items: List[PolicyResponse]

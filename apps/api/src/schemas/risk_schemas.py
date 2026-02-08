"""Risk management schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# Risk level constants for validation
RISK_LEVELS = ["low", "medium", "high", "critical"]
LIKELIHOOD_LEVELS = ["rare", "unlikely", "possible", "likely", "almost_certain"]
IMPACT_LEVELS = ["insignificant", "minor", "moderate", "major", "catastrophic"]
MITIGATION_STATUSES = ["not_started", "in_progress", "implemented", "monitored"]
LINK_TYPES = ["mitigates", "addresses", "monitors"]


class RiskCategoryCreate(BaseModel):
    """Schema for creating a risk category."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    risk_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    status: str = Field(default="active", pattern="^(active|inactive)$")


class RiskCategoryUpdate(BaseModel):
    """Schema for updating a risk category."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class RiskCategoryResponse(BaseModel):
    """Response schema for a risk category."""

    id: int
    category_id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    risk_level: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    children_count: Optional[int] = None
    entries_count: Optional[int] = None

    class Config:
        from_attributes = True


class RiskCategoryTreeResponse(BaseModel):
    """Response schema for a risk category with children."""

    id: int
    category_id: str
    name: str
    description: Optional[str] = None
    risk_level: str
    status: str
    children: List["RiskCategoryTreeResponse"] = []
    entries_count: int = 0


class RiskEntryCreate(BaseModel):
    """Schema for creating a risk entry."""

    category_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    inherent_risk_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    residual_risk_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    likelihood: Optional[str] = Field(
        None, pattern="^(rare|unlikely|possible|likely|almost_certain)$"
    )
    impact: Optional[str] = Field(
        None, pattern="^(insignificant|minor|moderate|major|catastrophic)$"
    )
    mitigation_status: str = Field(
        default="not_started", pattern="^(not_started|in_progress|implemented|monitored)$"
    )
    control_owner: Optional[str] = None
    review_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class RiskEntryUpdate(BaseModel):
    """Schema for updating a risk entry."""

    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    inherent_risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    residual_risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    likelihood: Optional[str] = Field(
        None, pattern="^(rare|unlikely|possible|likely|almost_certain)$"
    )
    impact: Optional[str] = Field(
        None, pattern="^(insignificant|minor|moderate|major|catastrophic)$"
    )
    mitigation_status: Optional[str] = Field(
        None, pattern="^(not_started|in_progress|implemented|monitored)$"
    )
    control_owner: Optional[str] = None
    review_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class RiskEntryResponse(BaseModel):
    """Response schema for a risk entry."""

    id: int
    risk_id: str
    category_id: int
    category_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    inherent_risk_level: str
    residual_risk_level: str
    likelihood: Optional[str] = None
    impact: Optional[str] = None
    mitigation_status: str
    control_owner: Optional[str] = None
    review_date: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: Optional[str] = None
    linked_obligations_count: Optional[int] = None

    class Config:
        from_attributes = True


class RiskEntryListResponse(BaseModel):
    """Response schema for paginated risk entry list."""

    total: int
    items: List[RiskEntryResponse]


class ObligationRiskLinkCreate(BaseModel):
    """Schema for linking an obligation to a risk entry."""

    obligation_id: int
    link_type: str = Field(default="mitigates", pattern="^(mitigates|addresses|monitors)$")
    notes: Optional[str] = None


class ObligationRiskLinkResponse(BaseModel):
    """Response schema for an obligation-risk link."""

    id: int
    obligation_id: int
    risk_entry_id: int
    link_type: str
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str
    obligation_text: Optional[str] = None
    obligation_article_ref: Optional[str] = None

    class Config:
        from_attributes = True


class RiskMapSummary(BaseModel):
    """Response schema for risk map overview."""

    total_categories: int
    total_entries: int
    by_inherent_level: Dict[str, int]
    by_residual_level: Dict[str, int]
    by_mitigation_status: Dict[str, int]
    by_category: List[Dict[str, Any]]
    high_priority_risks: List[RiskEntryResponse]


class RiskHeatMapCell(BaseModel):
    """Single cell in risk heat map."""

    likelihood: str
    impact: str
    count: int
    risk_ids: List[str]


class RiskHeatMapResponse(BaseModel):
    """Response schema for risk heat map visualization."""

    cells: List[RiskHeatMapCell]
    total_risks: int


# Enable forward references
RiskCategoryTreeResponse.model_rebuild()

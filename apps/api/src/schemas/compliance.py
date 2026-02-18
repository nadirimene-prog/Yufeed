from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime


# Enums (Re-declared for Pydantic to avoid Circular Imports with SQLAlchemy models if passing enums)
class ComplianceStatus(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class RiskLevel(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- base Schemas ---


class ComplianceDocumentBase(BaseModel):
    document_type: str
    file_url: str


class ComplianceDocumentCreate(ComplianceDocumentBase):
    pass


class ComplianceDocumentRead(ComplianceDocumentBase):
    id: int
    tenant_id: Optional[str] = None
    verification_status: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    vendor_verification_id: Optional[str] = None
    vendor_response: Optional[Dict[str, Any]] = None
    expiry_date: Optional[datetime] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class RiskSignalBase(BaseModel):
    signal_type: str
    score: int
    description: Optional[str] = None


class RiskSignalRead(RiskSignalBase):
    id: int
    detected_at: datetime

    class Config:
        from_attributes = True


# --- Profile Schemas ---


class ComplianceProfileBase(BaseModel):
    type: Literal["kyc", "kyb"]


class KYCProfileCreate(ComplianceProfileBase):
    type: Literal["kyc"] = "kyc"
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class KYBProfileCreate(ComplianceProfileBase):
    type: Literal["kyb"] = "kyb"
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    company_name: str
    registration_number: str
    jurisdiction: str
    website: Optional[str] = None
    industry: Optional[str] = None


# --- Read Schemas ---


class ComplianceProfileRead(BaseModel):
    id: int
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    status: str
    risk_level: str
    cdd_level: Optional[str] = None
    cdd_reason: Optional[str] = None
    next_review_date: Optional[datetime] = None
    last_review_date: Optional[datetime] = None
    review_frequency_months: Optional[int] = None
    pep_status: Optional[str] = None
    pep_details: Optional[Dict[str, Any]] = None
    sanctions_screened_at: Optional[datetime] = None
    sanctions_status: Optional[str] = None
    adverse_media_status: Optional[str] = None
    source_of_funds: Optional[str] = None
    source_of_wealth: Optional[str] = None
    occupation: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    type: str  # kyc or kyb

    # Common display fields (optional in base, filled by subclasses)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    registration_number: Optional[str] = None

    documents: List[ComplianceDocumentRead] = Field(default_factory=list)
    risk_signals: List[RiskSignalRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class KYCProfileRead(ComplianceProfileRead):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    nationality: Optional[str] = None
    tax_id: Optional[str] = None
    id_document_type: Optional[str] = None
    id_document_number: Optional[str] = None
    id_expiry_date: Optional[datetime] = None


class KYBProfileRead(ComplianceProfileRead):
    company_name: str
    registration_number: str
    jurisdiction: str
    website: Optional[str] = None
    industry: Optional[str] = None
    legal_form: Optional[str] = None
    incorporation_date: Optional[datetime] = None
    annual_turnover: Optional[str] = None
    number_of_employees: Optional[int] = None
    beneficial_ownership_chain: Optional[Dict[str, Any] | List[Any]] = None


# --- Update Schemas ---


class ReviewAction(BaseModel):
    action: Literal["approve", "reject"]
    reason: Optional[str] = None


class KYCScreenResponse(BaseModel):
    profile_id: int
    sanctions_status: str
    screened_at: datetime
    is_hit: bool
    highest_score: float
    match_count: int
    findings_created: int


class DocumentVerificationResponse(BaseModel):
    profile_id: int
    processed_count: int
    verified_count: int
    rejected_count: int
    error_count: int
    findings_created: int
    documents: List[ComplianceDocumentRead] = Field(default_factory=list)


class SetCDDLevelRequest(BaseModel):
    cdd_level: Literal["simplified", "standard", "enhanced"]
    reason: Optional[str] = None


class KYCReviewListResponse(BaseModel):
    total_due: int
    items: List[ComplianceProfileRead] = Field(default_factory=list)


class KYCReviewResponse(BaseModel):
    profile_id: int
    status: str
    last_review_date: datetime
    next_review_date: Optional[datetime] = None

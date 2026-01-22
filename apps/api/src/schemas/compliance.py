from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List, Literal
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
    verification_status: str
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
    type: Literal['kyc', 'kyb'] 

class KYCProfileCreate(ComplianceProfileBase):
    type: Literal['kyc'] = 'kyc'
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class KYBProfileCreate(ComplianceProfileBase):
    type: Literal['kyb'] = 'kyb'
    company_name: str
    registration_number: str
    jurisdiction: str
    website: Optional[str] = None
    industry: Optional[str] = None

# --- Read Schemas ---

class ComplianceProfileRead(BaseModel):
    id: int
    status: str
    risk_level: str
    created_at: datetime
    updated_at: datetime
    type: str # kyc or kyb
    
    # Common display fields (optional in base, filled by subclasses)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    registration_number: Optional[str] = None

    documents: List[ComplianceDocumentRead] = []
    risk_signals: List[RiskSignalRead] = []

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

class KYBProfileRead(ComplianceProfileRead):
    company_name: str
    registration_number: str
    jurisdiction: str
    website: Optional[str] = None
    industry: Optional[str] = None

# --- Update Schemas ---

class ReviewAction(BaseModel):
    action: Literal['approve', 'reject']
    reason: Optional[str] = None

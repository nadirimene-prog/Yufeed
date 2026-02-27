from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime, timezone
from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class ComplianceStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceProfile(Base):
    __tablename__ = "compliance_profiles"
    __table_args__ = (Index("ix_compliance_profiles_tenant_status", "tenant_id", "status"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), nullable=False, default="default", index=True)
    user_id = Column(String(255), nullable=True, index=True)
    status = Column(String, default=ComplianceStatus.PENDING)
    risk_level = Column(String, default=RiskLevel.LOW)
    cdd_level = Column(String(32), nullable=False, default="standard")
    cdd_reason = Column(Text, nullable=True)
    next_review_date = Column(DateTime, nullable=True, index=True)
    last_review_date = Column(DateTime, nullable=True)
    review_frequency_months = Column(Integer, nullable=True)
    pep_status = Column(String(20), nullable=False, default="unknown")
    pep_details = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    sanctions_screened_at = Column(DateTime, nullable=True)
    sanctions_status = Column(String(20), nullable=True)  # clear|hit|pending|error
    adverse_media_status = Column(String(20), nullable=True)  # clear|hit|pending|error
    source_of_funds = Column(Text, nullable=True)
    source_of_wealth = Column(Text, nullable=True)
    occupation = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Polymorphic identity
    type = Column(String)

    documents = relationship("ComplianceDocument", back_populates="profile")
    risk_signals = relationship("RiskSignal", back_populates="profile")

    __mapper_args__ = {"polymorphic_identity": "compliance_profile", "polymorphic_on": type}


class KYCProfile(ComplianceProfile):
    __tablename__ = "compliance_kyc_profiles"

    id = Column(Integer, ForeignKey("compliance_profiles.id"), primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, index=True, nullable=False)
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    address_line1 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)  # ISO code
    nationality = Column(String(2), nullable=True)
    tax_id = Column(String(255), nullable=True)
    id_document_type = Column(String(50), nullable=True)
    id_document_number = Column(String(255), nullable=True)
    id_expiry_date = Column(DateTime, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "kyc",
    }


class KYBProfile(ComplianceProfile):
    __tablename__ = "compliance_kyb_profiles"

    id = Column(Integer, ForeignKey("compliance_profiles.id"), primary_key=True)
    company_name = Column(String, nullable=False)
    registration_number = Column(String, nullable=False, index=True)
    jurisdiction = Column(String, nullable=False)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    legal_form = Column(String(100), nullable=True)
    incorporation_date = Column(DateTime, nullable=True)
    annual_turnover = Column(String(255), nullable=True)
    number_of_employees = Column(Integer, nullable=True)
    beneficial_ownership_chain = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "kyb",
    }


class ComplianceDocument(Base):
    __tablename__ = "compliance_documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), nullable=False, default="default", index=True)
    profile_id = Column(Integer, ForeignKey("compliance_profiles.id"))
    document_type = Column(String, nullable=False)  # e.g., passport, utility_bill
    file_url = Column(String, nullable=False)
    verification_status = Column(String, default="pending")
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    vendor_verification_id = Column(String(255), nullable=True)
    vendor_response = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    expiry_date = Column(DateTime, nullable=True, index=True)
    uploaded_at = Column(DateTime, default=utc_now)

    profile = relationship("ComplianceProfile", back_populates="documents")


class RiskSignal(Base):
    __tablename__ = "compliance_risk_signals"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), nullable=False, default="default", index=True)
    profile_id = Column(Integer, ForeignKey("compliance_profiles.id"))
    user_id = Column(String(255), nullable=True, index=True)
    signal_type = Column(String, nullable=False)  # e.g., ip_mismatch, pep_match
    score = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=utc_now)

    profile = relationship("ComplianceProfile", back_populates="risk_signals")

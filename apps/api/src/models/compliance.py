from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, JSON
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

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default=ComplianceStatus.PENDING)
    risk_level = Column(String, default=RiskLevel.LOW)
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

    __mapper_args__ = {
        "polymorphic_identity": "kyb",
    }


class ComplianceDocument(Base):
    __tablename__ = "compliance_documents"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("compliance_profiles.id"))
    document_type = Column(String, nullable=False)  # e.g., passport, utility_bill
    file_url = Column(String, nullable=False)
    verification_status = Column(String, default="pending")
    uploaded_at = Column(DateTime, default=utc_now)

    profile = relationship("ComplianceProfile", back_populates="documents")


class RiskSignal(Base):
    __tablename__ = "compliance_risk_signals"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("compliance_profiles.id"))
    signal_type = Column(String, nullable=False)  # e.g., ip_mismatch, pep_match
    score = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=utc_now)

    profile = relationship("ComplianceProfile", back_populates="risk_signals")

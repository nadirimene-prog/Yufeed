"""Compliance calendar model."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database import Base
from src.utils.time import utc_now


class ComplianceCalendarEvent(Base):
    __tablename__ = "compliance_calendar_events"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "fingerprint", name="uq_compliance_calendar_tenant_fingerprint"
        ),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    fingerprint = Column(String(128), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True, index=True)

    regulation_doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=True, index=True)
    obligation_id = Column(
        Integer, ForeignKey("regulatory_obligations.id"), nullable=True, index=True
    )
    policy_id = Column(Integer, ForeignKey("policy_documents.id"), nullable=True, index=True)
    compliance_profile_id = Column(
        Integer, ForeignKey("compliance_profiles.id"), nullable=True, index=True
    )

    status = Column(String(32), nullable=False, default="pending", index=True)
    assigned_to = Column(String(255), nullable=True, index=True)
    priority = Column(String(16), nullable=False, default="medium")
    reminder_days_before = Column(Integer, nullable=False, default=7)
    reminder_count = Column(Integer, nullable=False, default=0)
    last_reminder_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"), nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    regulation_doc = relationship("LegalDocument")
    obligation = relationship("RegulatoryObligation")
    policy = relationship("PolicyDocument")
    compliance_profile = relationship("ComplianceProfile")

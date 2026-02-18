"""Finding models (finding-first workbench).

A Finding is a normalized signal that requires triage. It may be escalated
into a Case for investigation.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    JSON,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database import Base
from src.utils.time import utc_now
from src.models.associations import case_findings


class FindingStatus(str, enum.Enum):
    new = "new"
    triaged = "triaged"
    closed = "closed"
    escalated = "escalated"


class FindingType(str, enum.Enum):
    """Standard finding types emitted by source domains."""

    TX_ALERT = "TX_ALERT"
    OBLIGATION_BREACH = "OBLIGATION_BREACH"
    SANCTIONS_HIT = "SANCTIONS_HIT"
    KYC_FAILURE = "KYC_FAILURE"
    KYC_EXPIRY = "KYC_EXPIRY"
    ONBOARDING_RISK = "ONBOARDING_RISK"
    EDD_TRIGGER = "EDD_TRIGGER"
    REG_CHANGE = "REG_CHANGE"
    ONCHAIN_RISK = "ONCHAIN_RISK"
    OTHER = "OTHER"


class FindingClosedReason(str, enum.Enum):
    """Reasons for closing a finding without escalation."""

    false_positive = "false_positive"
    resolved = "resolved"
    duplicate = "duplicate"
    not_applicable = "not_applicable"
    other = "other"


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "fingerprint", name="uq_findings_tenant_fingerprint"),
        Index("ix_findings_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ix_findings_tenant_severity_status", "tenant_id", "severity", "status"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)

    # Normalized type of signal
    finding_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=True, index=True)  # low|medium|high|critical
    status = Column(String(20), nullable=False, default=FindingStatus.new.value, index=True)

    title = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)

    # Pointers to source entities (alert_id, transaction_id, celex, obligation_id, chunk_ids, etc.)
    source_refs_json = Column(
        "source_refs",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    # Used for dedup/merge. Enforced unique per tenant.
    fingerprint = Column(String(128), nullable=False, index=True)

    # Why this finding exists (rule triggers, features, matches, citations)
    explainability_json = Column(
        "explainability",
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    assigned_to = Column(String(255), nullable=True, index=True)
    sla_due_at = Column(DateTime, nullable=True, index=True)

    # Close metadata
    closed_reason = Column(String(50), nullable=True)
    closed_comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    cases = relationship(
        "Case",
        secondary=case_findings,
        back_populates="findings",
        lazy="selectin",
    )

    @property
    def source_refs(self):
        """API-facing alias for serialized source references."""
        return self.source_refs_json

    @source_refs.setter
    def source_refs(self, value):
        self.source_refs_json = value

    @property
    def explainability(self):
        """API-facing alias for serialized explainability payload."""
        return self.explainability_json

    @explainability.setter
    def explainability(self, value):
        self.explainability_json = value

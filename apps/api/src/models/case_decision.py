"""CaseDecision model — governance-grade decision workflow.

A CaseDecision records a formal compliance decision for a Case.
Lifecycle: draft → submitted → approved / rejected.
Supports 4-eyes principle (approver must differ from creator).

NOTE: This is *not* the same as ``DecisionRecord`` in ``audit/models.py``
which captures real-time risk decisioning (allow/block/step_up).
"""

import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database import Base
from src.utils.time import utc_now


class CaseDecisionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class CaseDecisionDisposition(str, enum.Enum):
    """Outcome the investigator proposes for the case."""

    no_action = "no_action"
    false_positive = "false_positive"
    monitor = "monitor"
    remediate = "remediate"
    escalate = "escalate"
    sar_required = "sar_required"
    report_required = "report_required"
    other = "other"


class CaseDecision(Base):
    __tablename__ = "case_decisions"
    __table_args__ = (
        Index("ix_case_decisions_case_id", "case_id"),
        Index("ix_case_decisions_tenant_status", "tenant_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)

    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default=CaseDecisionStatus.draft.value)
    disposition = Column(String(50), nullable=False)
    rationale = Column(Text, nullable=True)

    # Author / submitter
    created_by = Column(String(255), nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    # Approver (4-eyes: must differ from created_by)
    approver_id = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    case = relationship("Case", backref="decisions")

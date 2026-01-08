"""
Impact Assessment models for regulatory compliance.
Helps AMLROs understand how regulations affect their operations.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum
from datetime import datetime
from src.database import Base


class ImpactLevel(str, enum.Enum):
    """Impact severity levels."""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Significant changes needed
    MEDIUM = "medium"  # Moderate effort required
    LOW = "low"  # Minor adjustments needed
    MINIMAL = "minimal"  # Informational only


class BusinessArea(str, enum.Enum):
    """Bank functional areas affected by regulations."""
    ONBOARDING = "onboarding"  # Customer onboarding / KYC
    TRANSACTION_MONITORING = "transaction_monitoring"  # TM systems
    SCREENING = "screening"  # Sanctions / PEP screening
    REPORTING = "reporting"  # Regulatory reporting (SAR, CTR)
    DUE_DILIGENCE = "due_diligence"  # CDD / EDD processes
    RECORD_KEEPING = "record_keeping"  # Data retention
    TRAINING = "training"  # Staff training requirements
    GOVERNANCE = "governance"  # Policies / procedures
    TECHNOLOGY = "technology"  # IT systems / infrastructure
    THIRD_PARTY = "third_party"  # Vendor management
    RISK_ASSESSMENT = "risk_assessment"  # Risk rating
    COMPLIANCE_FUNCTION = "compliance_function"  # Compliance team


class ActionStatus(str, enum.Enum):
    """Status of implementation actions."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DEFERRED = "deferred"


class ImpactAssessment(Base):
    """
    Impact assessment for a legal document.
    Analyzes how the regulation affects the bank's operations.
    """
    __tablename__ = "impact_assessments"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False, unique=True)

    # Overall assessment
    overall_impact_level = Column(SQLEnum(ImpactLevel), nullable=False)
    executive_summary = Column(Text, nullable=True)  # AI-generated summary for executives

    # Affected areas (array of BusinessArea enums)
    affected_areas_json = Column(JSONB, nullable=True)  # List of affected business areas

    # Analysis details
    key_changes = Column(JSONB, nullable=True)  # List of key changes introduced
    new_obligations = Column(JSONB, nullable=True)  # New obligations created
    modified_obligations = Column(JSONB, nullable=True)  # Changes to existing obligations

    # Resource estimates
    estimated_effort_hours = Column(Integer, nullable=True)  # Total effort estimate
    estimated_cost = Column(Integer, nullable=True)  # Cost estimate in EUR
    requires_system_changes = Column(Boolean, default=False)
    requires_process_changes = Column(Boolean, default=False)
    requires_policy_updates = Column(Boolean, default=False)

    # Metadata
    assessed_by = Column(String, nullable=True)  # User who created/approved assessment
    assessed_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("LegalDocument", backref="impact_assessment")
    action_items = relationship("ActionItem", back_populates="assessment", cascade="all, delete-orphan")


class ActionItem(Base):
    """
    Specific action items required to implement a regulation.
    Provides a task list for compliance teams.
    """
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("impact_assessments.id"), nullable=False)

    # Action details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    business_area = Column(SQLEnum(BusinessArea), nullable=False)

    # Priority and effort
    priority = Column(Integer, nullable=False, default=3)  # 1=highest, 5=lowest
    estimated_hours = Column(Integer, nullable=True)
    complexity = Column(String, nullable=True)  # "simple", "moderate", "complex"

    # Assignment and tracking
    assigned_to = Column(String, nullable=True)  # Email or username
    status = Column(SQLEnum(ActionStatus), default=ActionStatus.NOT_STARTED)

    # Deadlines
    target_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Dependencies
    depends_on_action_ids = Column(JSONB, nullable=True)  # List of action IDs this depends on
    blocks_action_ids = Column(JSONB, nullable=True)  # List of action IDs blocked by this

    # Notes and progress
    notes = Column(Text, nullable=True)
    progress_percentage = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("ImpactAssessment", back_populates="action_items")


class GapAnalysis(Base):
    """
    Gap analysis comparing current state vs required state.
    Identifies what needs to change to achieve compliance.
    """
    __tablename__ = "gap_analyses"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("impact_assessments.id"), nullable=False)

    # Gap details
    gap_category = Column(String, nullable=False)  # e.g., "policy", "process", "technology"
    current_state = Column(Text, nullable=False)  # What we have now
    required_state = Column(Text, nullable=False)  # What regulation requires
    gap_description = Column(Text, nullable=True)  # The delta

    # Impact
    severity = Column(SQLEnum(ImpactLevel), nullable=False)
    business_area = Column(SQLEnum(BusinessArea), nullable=False)

    # Remediation
    remediation_approach = Column(Text, nullable=True)  # How to close the gap
    estimated_cost = Column(Integer, nullable=True)
    estimated_timeline_days = Column(Integer, nullable=True)

    # Status
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("ImpactAssessment", backref="gaps")

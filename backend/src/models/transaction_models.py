"""
Transaction Monitoring Models
Phase 1: Foundation for transaction monitoring, alerts, and case management.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, Boolean,
    ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base


class Transaction(Base):
    """Transaction data model with risk scoring and geographic information."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    transaction_type = Column(String(50))  # 'deposit', 'withdrawal', 'transfer', 'payment'
    counterparty_id = Column(String(255))
    counterparty_name = Column(String(500))
    timestamp = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default='completed')  # 'pending', 'completed', 'flagged', 'blocked'

    # Geographic data
    ip_address = Column(INET)
    country_code = Column(String(2))
    geo_location = Column(String(255))

    # Risk data
    risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))  # 'low', 'medium', 'high', 'critical'
    risk_factors = Column(JSONB)

    # Metadata
    device_fingerprint = Column(String(255))
    session_id = Column(String(255))
    metadata = Column(JSONB)
    description = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="transaction")


class Alert(Base):
    """Alert model with regulatory context and case management integration."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    alert_id = Column(String(255), unique=True, nullable=False, index=True)
    alert_type = Column(String(100), nullable=False)  # 'velocity', 'structuring', 'unusual_pattern', etc.
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'

    # Triggered by
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    user_id = Column(String(255), index=True)
    rule_id = Column(String(255))

    # Status workflow
    status = Column(String(50), default='pending')  # 'pending', 'in_review', 'escalated', 'resolved', 'false_positive'
    assigned_to = Column(String(255))
    priority = Column(Integer, default=3)  # 1 (highest) to 5 (lowest)

    # Alert details
    description = Column(Text)
    risk_score = Column(Numeric(5, 2))
    matched_rules = Column(JSONB)
    evidence = Column(JSONB)

    # REGULATORY CONTEXT (Yufeed Innovation)
    related_regulations = Column(JSONB)  # Array of LegalDocument IDs
    regulation_context = Column(Text)  # AI-generated explanation

    # Resolution
    resolution_status = Column(String(50))
    resolution_notes = Column(Text)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime)

    # SAR filing
    sar_filed = Column(Boolean, default=False)
    sar_id = Column(String(255))
    sar_filed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="alerts")


class Case(Base):
    """Investigation case model with regulatory linkage."""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)
    case_id = Column(String(255), unique=True, nullable=False, index=True)
    case_type = Column(String(100))  # 'investigation', 'sar_preparation', 'audit'
    subject_type = Column(String(50))  # 'user', 'transaction', 'pattern'
    subject_id = Column(String(255), index=True)

    # Status
    status = Column(String(50), default='open')  # 'open', 'in_progress', 'escalated', 'closed'
    priority = Column(String(20), default='medium')  # 'low', 'medium', 'high', 'critical'

    # Assignment
    assigned_to = Column(String(255))
    team = Column(String(100))

    # Content
    title = Column(String(500))
    description = Column(Text)
    summary = Column(Text)

    # Related entities (using PostgreSQL arrays)
    related_alert_ids = Column(ARRAY(Integer))
    related_transaction_ids = Column(ARRAY(Integer))
    related_users = Column(ARRAY(String(255)))

    # REGULATORY LINKAGE (Yufeed Innovation)
    applicable_regulation_ids = Column(ARRAY(Integer))  # LegalDocument IDs
    regulatory_violations = Column(JSONB)

    # Evidence
    evidence = Column(JSONB)
    attachments = Column(JSONB)

    # Timeline
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)

    # Outcomes
    outcome = Column(String(100))  # 'sar_filed', 'no_action', 'account_closed', 'escalated'
    outcome_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitoringRule(Base):
    """Monitoring rule model with regulatory basis."""
    __tablename__ = "monitoring_rules"

    id = Column(Integer, primary_key=True)
    rule_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)

    # Rule type
    category = Column(String(100))  # 'velocity', 'structuring', 'unusual_behavior', 'sanctions'
    severity = Column(String(20), default='medium')

    # Rule logic (JSON-based DSL)
    conditions = Column(JSONB, nullable=False)
    thresholds = Column(JSONB)

    # Regulatory basis (YUFEED INNOVATION)
    regulatory_source_id = Column(Integer, ForeignKey('legal_documents.id'), nullable=True)
    regulation_article = Column(String(255))
    regulatory_requirement = Column(Text)

    # Status
    enabled = Column(Boolean, default=True)
    version = Column(Integer, default=1)

    # Performance tracking
    alert_count = Column(Integer, default=0)
    true_positive_rate = Column(Numeric(5, 2))
    false_positive_rate = Column(Numeric(5, 2))

    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    regulatory_source = relationship("LegalDocument", foreign_keys=[regulatory_source_id])


class UserRiskProfile(Base):
    """User risk profile model with behavioral patterns and KYC status."""
    __tablename__ = "user_risk_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)

    # Computed risk
    overall_risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))  # 'low', 'medium', 'high', 'critical'
    risk_factors = Column(JSONB)

    # Behavioral patterns
    transaction_velocity_30d = Column(Integer)
    average_transaction_amount = Column(Numeric(15, 2))
    total_transaction_amount_30d = Column(Numeric(15, 2))
    transaction_pattern_score = Column(Numeric(5, 2))

    # KYC/CDD status
    kyc_status = Column(String(50))
    kyc_last_updated = Column(DateTime)
    enhanced_due_diligence = Column(Boolean, default=False)

    # Geographic risk
    primary_country = Column(String(2))
    high_risk_jurisdictions = Column(ARRAY(String(2)))

    # Alerts history
    total_alerts = Column(Integer, default=0)
    critical_alerts = Column(Integer, default=0)
    resolved_alerts = Column(Integer, default=0)

    # Sanctions screening
    sanctions_screened_at = Column(DateTime)
    sanctions_match = Column(Boolean, default=False)
    sanctions_details = Column(JSONB)

    # Account metadata
    account_created_at = Column(DateTime)
    last_activity_at = Column(DateTime)

    last_calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeatureValue(Base):
    """Feature store model for ML features and risk scoring."""
    __tablename__ = "feature_values"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50), nullable=False)  # 'transaction', 'user', 'session'
    entity_id = Column(String(255), nullable=False)

    # Feature data
    feature_name = Column(String(255), nullable=False)
    feature_value = Column(JSONB, nullable=False)
    feature_type = Column(String(50))  # 'numeric', 'categorical', 'boolean', 'text'

    # Metadata
    calculated_at = Column(DateTime, nullable=False)
    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)

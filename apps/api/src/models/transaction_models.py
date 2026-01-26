"""
Transaction Monitoring Models
Phase 1: Foundation for transaction monitoring, alerts, and case management.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, Boolean,
    ForeignKey, ARRAY, JSON
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base


class Transaction(Base):
    """Transaction data model with risk scoring and geographic information."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
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
    ip_address = Column(String(45).with_variant(INET(), "postgresql"))
    country_code = Column(String(2), index=True)  # Indexed for country-based filtering
    geo_location = Column(String(255))

    # Risk data
    risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20), index=True)  # Indexed for risk-based filtering
    risk_factors = Column(JSON().with_variant(JSONB(), "postgresql"))

    # Metadata
    device_fingerprint = Column(String(255))
    session_id = Column(String(255))
    transaction_metadata = Column(JSON().with_variant(JSONB(), "postgresql"))
    description = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="transaction")


class Alert(Base):
    """Alert model with regulatory context and case management integration."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    alert_id = Column(String(255), unique=True, nullable=False, index=True)
    alert_type = Column(String(100), nullable=False)  # 'velocity', 'structuring', 'unusual_pattern', etc.
    severity = Column(String(20), nullable=False)  # 'low', 'medium', 'high', 'critical'

    # Triggered by
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True, index=True)  # Indexed for joins
    user_id = Column(String(255), index=True)

    # Status workflow
    status = Column(String(50), default='pending', index=True)  # Indexed for status filtering
    assigned_to = Column(String(255), index=True)  # Indexed for assignment queries
    priority = Column(Integer, default=3)  # 1 (highest) to 5 (lowest)

    # Alert details
    description = Column(Text)
    risk_score = Column(Numeric(5, 2))
    matched_rules_data = Column(JSON().with_variant(JSONB(), "postgresql"))  # Summary of matches
    evidence = Column(JSON().with_variant(JSONB(), "postgresql"))

    # REGULATORY CONTEXT (Yufeed Innovation)
    related_regulations = Column(JSON().with_variant(JSONB(), "postgresql"))  # Array of LegalDocument IDs
    regulation_context = Column(Text)  # AI-generated explanation

    # Resolution
    resolution_status = Column(String(50))
    resolution_notes = Column(Text)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime)

    # SAR filing
    sar_filed = Column(Boolean, default=False, index=True)  # Indexed for SAR queries
    sar_id = Column(String(255))
    sar_filed_at = Column(DateTime)

    # ML Triage (Phase 4B: Task 4.4)
    ml_prediction = Column(String(50))  # 'false_positive', 'true_positive', 'uncertain'
    ml_confidence = Column(Numeric(5, 4))  # 0.0000 to 1.0000
    ml_model_version = Column(String(50))  # Model version identifier
    ml_features_snapshot = Column(JSON().with_variant(JSONB(), "postgresql"))  # Features used for prediction

    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # Indexed for date range queries
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="alerts")
    rule_hits = relationship("RuleHit", back_populates="alert")


class Case(Base):
    """Investigation case model with regulatory linkage."""
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    case_id = Column(String(255), unique=True, nullable=False, index=True)
    case_type = Column(String(100))  # 'investigation', 'sar_preparation', 'audit'
    subject_type = Column(String(50))  # 'user', 'transaction', 'pattern'
    subject_id = Column(String(255), index=True)

    # Status
    status = Column(String(50), default='open', index=True)  # Indexed for status filtering
    priority = Column(String(20), default='medium', index=True)  # Indexed for priority sorting

    # Assignment
    assigned_to = Column(String(255), index=True)  # Indexed for assignment queries
    team = Column(String(100))

    # Content
    title = Column(String(500))
    description = Column(Text)
    summary = Column(Text)

    # Related entities (using PostgreSQL arrays)
    related_alert_ids = Column(JSON().with_variant(ARRAY(Integer), "postgresql"))
    related_transaction_ids = Column(JSON().with_variant(ARRAY(Integer), "postgresql"))
    related_users = Column(JSON().with_variant(ARRAY(String(255)), "postgresql"))

    # REGULATORY LINKAGE (Yufeed Innovation)
    applicable_regulation_ids = Column(JSON().with_variant(ARRAY(Integer), "postgresql"))  # LegalDocument IDs
    regulatory_violations = Column(JSON().with_variant(JSONB(), "postgresql"))

    # Evidence
    evidence = Column(JSON().with_variant(JSONB(), "postgresql"))
    attachments = Column(JSON().with_variant(JSONB(), "postgresql"))

    # Timeline
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)

    # Outcomes
    outcome = Column(String(100))  # 'sar_filed', 'no_action', 'account_closed', 'escalated'
    outcome_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitoringRule(Base):
    """Monitoring rule model with advanced logic and regulatory basis."""
    __tablename__ = "monitoring_rules"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    rule_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)

    # Rule type and priority
    category = Column(String(100))  # 'velocity', 'structuring', 'unusual_behavior', 'sanctions'
    severity = Column(String(20), default='medium')
    priority = Column(Integer, default=3)

    # Rule logic - Sardine-inspired nested logic
    # Schema: { "logic": "AND", "conditions": [ { "field": "amount", "operator": ">", "value": 1000 }, ... ] }
    conditions = Column("conditions", JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    
    # Aggregation requirements (e.g., lookback periods)
    # Schema: { "window_size": "24h", "metric": "sum", "field": "amount" }
    thresholds = Column("thresholds", JSON().with_variant(JSONB(), "postgresql"))

    # Regulatory basis (YUFEED INNOVATION)
    regulatory_source_id = Column(Integer, ForeignKey('legal_documents.id'), nullable=True)
    regulation_article = Column(String(255))
    regulatory_requirement = Column(Text)

    # Status and Versioning
    enabled = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)
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
    hits = relationship("RuleHit", back_populates="rule")
    versions = relationship("RuleVersion", back_populates="rule", cascade="all, delete-orphan")


class RuleVersion(Base):
    """Immutable version snapshots for monitoring rules."""
    __tablename__ = "rule_versions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    rule_id = Column(Integer, ForeignKey("monitoring_rules.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # draft | pending | approved | rejected

    name = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    severity = Column(String(20), default="medium")
    priority = Column(Integer, default=3)
    conditions = Column("conditions", JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    thresholds = Column("thresholds", JSON().with_variant(JSONB(), "postgresql"))
    enabled = Column(Boolean, default=True)

    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(255))
    approved_at = Column(DateTime)
    notes = Column(Text)

    rule = relationship("MonitoringRule", back_populates="versions")



class RuleHit(Base):
    """Records specific rule hits for an alert/transaction."""
    __tablename__ = "rule_hits"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    alert_id = Column(Integer, ForeignKey('alerts.id'), nullable=False)
    rule_id = Column(Integer, ForeignKey('monitoring_rules.id'), nullable=False)
    
    # Captured data at time of hit
    trigger_values = Column(JSON().with_variant(JSONB(), "postgresql")) 
    matched_conditions = Column(JSON().with_variant(JSONB(), "postgresql"))
    
    hit_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    alert = relationship("Alert", back_populates="rule_hits")
    rule = relationship("MonitoringRule", back_populates="hits")


class UserRiskProfile(Base):
    """User risk profile model with behavioral patterns and KYC status."""
    __tablename__ = "user_risk_profiles"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    user_id = Column(String(255), unique=True, nullable=False, index=True)

    # Computed risk
    overall_risk_score = Column(Numeric(5, 2))
    risk_level = Column(String(20))  # 'low', 'medium', 'high', 'critical'
    risk_factors = Column(JSON().with_variant(JSONB(), "postgresql"))

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
    high_risk_jurisdictions = Column(JSON().with_variant(ARRAY(String(2)), "postgresql"))

    # Alerts history
    total_alerts = Column(Integer, default=0)
    critical_alerts = Column(Integer, default=0)
    resolved_alerts = Column(Integer, default=0)

    # Sanctions screening
    sanctions_screened_at = Column(DateTime)
    sanctions_match = Column(Boolean, default=False)
    sanctions_details = Column(JSON().with_variant(JSONB(), "postgresql"))

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
    tenant_id = Column(String(255), nullable=False, index=True)  # Multi-tenancy support
    entity_type = Column(String(50), nullable=False)  # 'transaction', 'user', 'session'
    entity_id = Column(String(255), nullable=False)

    # Feature data
    feature_name = Column(String(255), nullable=False)
    feature_value = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    feature_type = Column(String(50))  # 'numeric', 'categorical', 'boolean', 'text'

    # Metadata
    calculated_at = Column(DateTime, nullable=False)
    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)

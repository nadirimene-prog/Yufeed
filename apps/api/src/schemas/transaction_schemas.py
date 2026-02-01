"""
Transaction Monitoring Pydantic Schemas
API request/response models for transaction monitoring system.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from decimal import Decimal


# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class TransactionBase(BaseModel):
    """Base transaction schema with common fields."""
    transaction_id: str = Field(..., max_length=255)
    user_id: str = Field(..., max_length=255)
    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field(..., max_length=3)
    transaction_type: Optional[str] = Field(None, max_length=50)
    counterparty_id: Optional[str] = Field(None, max_length=255)
    counterparty_name: Optional[str] = Field(None, max_length=500)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default='completed', max_length=50)

    # Geographic data
    ip_address: Optional[str] = None
    country_code: Optional[str] = Field(None, max_length=2)
    geo_location: Optional[str] = Field(None, max_length=255)

    # Metadata
    device_fingerprint: Optional[str] = Field(None, max_length=255)
    session_id: Optional[str] = Field(None, max_length=255)
    transaction_metadata: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @validator('currency')
    def currency_must_be_uppercase(cls, v):
        return v.upper()


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    pass


class TransactionUpdate(BaseModel):
    """Schema for updating transaction fields."""
    status: Optional[str] = None
    risk_score: Optional[Decimal] = None
    risk_level: Optional[str] = None
    risk_factors: Optional[Dict[str, Any]] = None


class TransactionResponse(TransactionBase):
    """Schema for transaction API response."""
    id: int
    risk_score: Optional[Decimal] = None
    risk_level: Optional[str] = None
    risk_factors: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertBase(BaseModel):
    """Base alert schema."""
    alert_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=20)
    user_id: str = Field(..., max_length=255)
    rule_id: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)


class AlertCreate(AlertBase):
    """Schema for creating a new alert."""
    transaction_id: Optional[int] = None
    risk_score: Optional[Decimal] = None
    matched_rules: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    related_regulations: Optional[List[int]] = None  # LegalDocument IDs
    regulation_context: Optional[str] = None


class AlertUpdate(BaseModel):
    """Schema for updating alert fields."""
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    resolution_status: Optional[str] = None
    resolution_notes: Optional[str] = None


class AlertResponse(AlertBase):
    """Schema for alert API response."""
    id: int
    alert_id: str
    transaction_id: Optional[int] = None
    status: str
    assigned_to: Optional[str] = None
    risk_score: Optional[Decimal] = None
    matched_rules: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    related_regulations: Optional[List[int]] = None
    regulation_context: Optional[str] = None
    resolution_status: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    sar_filed: bool
    sar_id: Optional[str] = None
    sar_filed_at: Optional[datetime] = None
    # Phase 4B: ML Triage fields
    ml_prediction: Optional[str] = None
    ml_confidence: Optional[Decimal] = None
    ml_model_version: Optional[str] = None
    ml_features_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CASE SCHEMAS
# ============================================================================

class CaseBase(BaseModel):
    """Base case schema."""
    case_type: Optional[str] = Field(None, max_length=100)
    subject_type: Optional[str] = Field(None, max_length=50)
    subject_id: Optional[str] = Field(None, max_length=255)
    priority: str = Field(default='medium', max_length=20)
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    team: Optional[str] = Field(None, max_length=100)


class CaseCreate(CaseBase):
    """Schema for creating a new case."""
    related_alert_ids: Optional[List[int]] = None
    related_transaction_ids: Optional[List[int]] = None
    related_users: Optional[List[str]] = None
    applicable_regulation_ids: Optional[List[int]] = None


class CaseUpdate(BaseModel):
    """Schema for updating case fields."""
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    summary: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    outcome: Optional[str] = None
    outcome_notes: Optional[str] = None


class CaseResponse(CaseBase):
    """Schema for case API response."""
    id: int
    case_id: str
    status: str
    assigned_to: Optional[str] = None
    summary: Optional[str] = None
    related_alert_ids: Optional[List[int]] = None
    related_transaction_ids: Optional[List[int]] = None
    related_users: Optional[List[str]] = None
    applicable_regulation_ids: Optional[List[int]] = None
    regulatory_violations: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    attachments: Optional[Dict[str, Any]] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    outcome: Optional[str] = None
    outcome_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING RULE SCHEMAS
# ============================================================================

class MonitoringRuleBase(BaseModel):
    """Base monitoring rule schema."""
    name: str = Field(..., max_length=500)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    severity: str = Field(default='medium', max_length=20)
    conditions: Dict[str, Any] = Field(..., description="JSON-based rule DSL")
    thresholds: Optional[Dict[str, Any]] = None


class MonitoringRuleCreate(MonitoringRuleBase):
    """Schema for creating a new monitoring rule."""
    regulatory_source_id: Optional[int] = None
    regulation_article: Optional[str] = Field(None, max_length=255)
    regulatory_requirement: Optional[str] = None
    enabled: bool = True


class MonitoringRuleUpdate(BaseModel):
    """Schema for updating monitoring rule fields."""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    thresholds: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None


class MonitoringRuleResponse(MonitoringRuleBase):
    """Schema for monitoring rule API response."""
    id: int
    rule_id: str
    regulatory_source_id: Optional[int] = None
    regulation_article: Optional[str] = None
    regulatory_requirement: Optional[str] = None
    enabled: bool
    version: int
    alert_count: int
    true_positive_rate: Optional[Decimal] = None
    false_positive_rate: Optional[Decimal] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# RULE VERSIONING SCHEMAS
# ============================================================================

class RuleVersionCreate(BaseModel):
    """Schema for creating a pending rule version."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    conditions: Optional[Dict[str, Any]] = None
    thresholds: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class RuleVersionResponse(BaseModel):
    """Schema for rule version response."""
    id: int
    rule_id: int
    version_number: int
    status: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    severity: str
    priority: int
    conditions: Dict[str, Any]
    thresholds: Optional[Dict[str, Any]] = None
    enabled: bool
    created_by: Optional[str] = None
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# RULE SIMULATION & BACKTEST SCHEMAS
# ============================================================================

class RuleSimulationRequest(BaseModel):
    """Schema for simulating a rule against a payload or transaction."""
    transaction_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class RuleSimulationResponse(BaseModel):
    """Schema for rule simulation response."""
    rule_id: str
    transaction_id: Optional[str] = None
    would_trigger: bool
    logic: str
    condition_results: List[Dict[str, Any]]
    evaluated_at: datetime


class RuleBacktestRequest(BaseModel):
    """Schema for rule backtest parameters."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(500, ge=1, le=5000)
    sample_size: int = Field(5, ge=0, le=50)


class RuleBacktestSample(BaseModel):
    """Schema for backtest sample rows."""
    transaction_id: str
    amount: Decimal
    currency: str
    transaction_type: Optional[str] = None
    country_code: Optional[str] = None
    timestamp: datetime
    would_trigger: bool


class RuleBacktestResponse(BaseModel):
    """Schema for rule backtest response."""
    rule_id: str
    total_transactions: int
    matches: int
    match_rate: float
    evaluated_at: datetime
    window: Dict[str, Optional[datetime]]
    samples: List[RuleBacktestSample]


# ============================================================================
# USER RISK PROFILE SCHEMAS
# ============================================================================

class UserRiskProfileBase(BaseModel):
    """Base user risk profile schema."""
    user_id: str = Field(..., max_length=255)


class UserRiskProfileUpdate(BaseModel):
    """Schema for updating user risk profile."""
    overall_risk_score: Optional[Decimal] = None
    risk_level: Optional[str] = None
    risk_factors: Optional[Dict[str, Any]] = None
    transaction_velocity_30d: Optional[int] = None
    average_transaction_amount: Optional[Decimal] = None
    total_transaction_amount_30d: Optional[Decimal] = None
    kyc_status: Optional[str] = None
    enhanced_due_diligence: Optional[bool] = None
    primary_country: Optional[str] = None
    sanctions_match: Optional[bool] = None


class UserRiskProfileResponse(UserRiskProfileBase):
    """Schema for user risk profile API response."""
    id: int
    overall_risk_score: Optional[Decimal] = None
    risk_level: Optional[str] = None
    risk_factors: Optional[Dict[str, Any]] = None
    transaction_velocity_30d: Optional[int] = None
    average_transaction_amount: Optional[Decimal] = None
    total_transaction_amount_30d: Optional[Decimal] = None
    transaction_pattern_score: Optional[Decimal] = None
    kyc_status: Optional[str] = None
    kyc_last_updated: Optional[datetime] = None
    enhanced_due_diligence: bool
    primary_country: Optional[str] = None
    high_risk_jurisdictions: Optional[List[str]] = None
    total_alerts: int
    critical_alerts: int
    resolved_alerts: int
    sanctions_screened_at: Optional[datetime] = None
    sanctions_match: bool
    sanctions_details: Optional[Dict[str, Any]] = None
    account_created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    last_calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# FEATURE VALUE SCHEMAS
# ============================================================================

class FeatureValueBase(BaseModel):
    """Base feature value schema."""
    entity_type: str = Field(..., max_length=50)
    entity_id: str = Field(..., max_length=255)
    feature_name: str = Field(..., max_length=255)
    feature_value: Dict[str, Any]
    feature_type: Optional[str] = Field(None, max_length=50)


class FeatureValueCreate(FeatureValueBase):
    """Schema for creating a new feature value."""
    calculated_at: datetime
    version: int = 1


class FeatureValueResponse(FeatureValueBase):
    """Schema for feature value API response."""
    id: int
    calculated_at: datetime
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING DASHBOARD SCHEMAS
# ============================================================================

class AlertStatistics(BaseModel):
    """Alert statistics for dashboard."""
    total_alerts: int
    pending_alerts: int
    in_review_alerts: int
    resolved_alerts: int
    false_positives: int
    critical_alerts: int
    high_severity_alerts: int
    alerts_by_type: Dict[str, int]
    alerts_by_status: Dict[str, int]
    by_status: Dict[str, int] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)


class TransactionStatistics(BaseModel):
    """Transaction statistics for dashboard."""
    total_transactions: int
    total_volume: Decimal
    flagged_transactions: int
    blocked_transactions: int
    high_risk_transactions: int
    transactions_by_country: Dict[str, int]
    transactions_by_type: Dict[str, int]
    average_transaction_amount: Decimal


class MonitoringDashboard(BaseModel):
    """Complete monitoring dashboard data."""
    alert_stats: AlertStatistics
    transaction_stats: TransactionStatistics
    top_risk_users: List[UserRiskProfileResponse]
    recent_alerts: List[AlertResponse]
    active_cases: List[CaseResponse]
    rule_performance: List[MonitoringRuleResponse]

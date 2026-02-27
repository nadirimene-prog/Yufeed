"""
AI Usage tracking models for cost monitoring and budgeting.
Tracks API calls, token usage, and estimated costs across tenants.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class AIUsageLog(Base):
    """
    Log of AI API usage for cost tracking and analytics.

    Enables:
    - Per-tenant cost tracking
    - Daily/monthly budget alerts
    - Model usage analysis
    - Cost optimization insights
    """

    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True)

    # Tenant isolation
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=False)

    # API details
    provider = Column(String(50), nullable=False)  # "openai", "anthropic", "azure"
    model = Column(String(100), nullable=False)  # "gpt-4", "claude-3-opus", etc.

    # Usage metrics
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # Cost estimation (USD)
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)

    # Context
    operation = Column(
        String(100), nullable=True
    )  # "obligation_extraction", "policy_analysis", etc.
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=True)
    obligation_id = Column(Integer, ForeignKey("regulatory_obligations.id"), nullable=True)
    user_id = Column(String(255), nullable=True)  # User who triggered the request

    # Metadata
    request_metadata = Column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )  # Additional context (model version, temperature, etc.)
    response_metadata = Column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )  # Response details (finish_reason, etc.)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_ai_usage_tenant_created", "tenant_id", "created_at"),
        Index("idx_ai_usage_provider_model", "provider", "model"),
        Index("idx_ai_usage_operation", "operation"),
    )


class AIBudget(Base):
    """
    AI usage budgets per tenant.
    Enables cost control and alerting.
    """

    __tablename__ = "ai_budgets"

    id = Column(Integer, primary_key=True, index=True)

    # Tenant isolation
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, unique=True)

    # Budget limits (USD)
    daily_limit_usd = Column(Float, nullable=False, default=100.0)
    monthly_limit_usd = Column(Float, nullable=False, default=3000.0)

    # Current usage (USD) - reset periodically
    daily_usage_usd = Column(Float, nullable=False, default=0.0)
    monthly_usage_usd = Column(Float, nullable=False, default=0.0)

    # Reset tracking
    daily_reset_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    monthly_reset_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Alert thresholds (percentage of limit)
    warning_threshold_percent = Column(Integer, default=80)  # Alert at 80% usage
    critical_threshold_percent = Column(Integer, default=95)  # Critical alert at 95%

    # Alert state
    daily_warning_sent = Column(DateTime(timezone=True), nullable=True)
    daily_critical_sent = Column(DateTime(timezone=True), nullable=True)
    monthly_warning_sent = Column(DateTime(timezone=True), nullable=True)
    monthly_critical_sent = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

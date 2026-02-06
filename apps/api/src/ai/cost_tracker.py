"""
AI cost tracking utilities.

Tracks AI API usage to database for cost monitoring and budgeting.
"""
from typing import Any, Dict, Optional
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from src.models.ai_usage_models import AIUsageLog, AIBudget
from src.monitoring.metrics import (
    ai_api_calls_total,
    ai_api_tokens_used_total,
    ai_api_cost_usd,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# Cost per 1K tokens (USD) - update periodically from provider pricing
AI_COST_CONFIG = {
    "openai": {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    },
    "anthropic": {
        "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
        "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
        "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
    },
    "azure": {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-35-turbo": {"prompt": 0.002, "completion": 0.002},
    },
}


def estimate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int
) -> float:
    """
    Estimate cost based on token usage.

    Args:
        provider: AI provider (openai, anthropic, azure)
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Estimated cost in USD
    """
    if provider not in AI_COST_CONFIG:
        logger.warning(f"Unknown AI provider: {provider}")
        return 0.0

    if model not in AI_COST_CONFIG[provider]:
        logger.warning(f"Unknown model: {model} for provider {provider}")
        return 0.0

    pricing = AI_COST_CONFIG[provider][model]

    # Cost per 1K tokens
    prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * pricing["completion"]

    return round(prompt_cost + completion_cost, 6)


def log_usage(
    db: Session,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    tenant_id: str,
    operation: Optional[str] = None,
    document_id: Optional[int] = None,
    obligation_id: Optional[int] = None,
    user_id: Optional[str] = None,
    request_metadata: Optional[Dict[str, Any]] = None,
    response_metadata: Optional[Dict[str, Any]] = None,
) -> AIUsageLog:
    """
    Log AI API usage to database and update metrics.

    Args:
        db: Database session
        provider: AI provider (openai, anthropic, azure)
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        tenant_id: Tenant ID for isolation
        operation: Operation context (e.g., "obligation_extraction")
        document_id: Related document ID
        obligation_id: Related obligation ID
        user_id: User who triggered the request
        request_metadata: Additional request context
        response_metadata: Additional response details

    Returns:
        Created AIUsageLog record
    """
    try:
        # Estimate cost
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = estimate_cost(provider, model, prompt_tokens, completion_tokens)

        # Create usage log
        usage_log = AIUsageLog(
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            operation=operation,
            document_id=document_id,
            obligation_id=obligation_id,
            user_id=user_id,
            request_metadata=request_metadata,
            response_metadata=response_metadata,
            created_at=utc_now(),
        )

        db.add(usage_log)
        db.commit()

        # Update Prometheus metrics
        ai_api_calls_total.labels(
            provider=provider,
            model=model,
            tenant_id=tenant_id
        ).inc()

        ai_api_tokens_used_total.labels(
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            type="prompt"
        ).inc(prompt_tokens)

        ai_api_tokens_used_total.labels(
            provider=provider,
            model=model,
            tenant_id=tenant_id,
            type="completion"
        ).inc(completion_tokens)

        ai_api_cost_usd.labels(
            provider=provider,
            model=model,
            tenant_id=tenant_id
        ).inc(estimated_cost)

        # Update budget tracking
        _update_budget_usage(db, tenant_id, estimated_cost)

        logger.info(
            f"AI usage logged: {operation or 'unknown'} - {provider}/{model} - "
            f"{total_tokens} tokens - ${estimated_cost:.4f}",
            extra={
                "tenant_id": tenant_id,
                "provider": provider,
                "model": model,
                "tokens": total_tokens,
                "cost_usd": estimated_cost,
            }
        )

        return usage_log

    except Exception as exc:
        logger.error(f"Failed to log AI usage: {exc}", exc_info=True)
        db.rollback()
        raise


def _update_budget_usage(db: Session, tenant_id: str, cost_usd: float):
    """Update tenant's budget usage and check thresholds."""
    try:
        # Get or create budget
        budget = db.query(AIBudget).filter(AIBudget.tenant_id == tenant_id).first()

        if not budget:
            # Create default budget
            budget = AIBudget(
                tenant_id=tenant_id,
                daily_limit_usd=100.0,
                monthly_limit_usd=3000.0,
                daily_usage_usd=0.0,
                monthly_usage_usd=0.0,
                daily_reset_at=utc_now(),
                monthly_reset_at=utc_now(),
            )
            db.add(budget)

        # Check if reset needed
        now = utc_now()

        # Daily reset (24 hours)
        if now >= budget.daily_reset_at + timedelta(days=1):
            budget.daily_usage_usd = 0.0
            budget.daily_reset_at = now
            budget.daily_warning_sent = None
            budget.daily_critical_sent = None

        # Monthly reset (30 days)
        if now >= budget.monthly_reset_at + timedelta(days=30):
            budget.monthly_usage_usd = 0.0
            budget.monthly_reset_at = now
            budget.monthly_warning_sent = None
            budget.monthly_critical_sent = None

        # Update usage
        budget.daily_usage_usd += cost_usd
        budget.monthly_usage_usd += cost_usd
        budget.updated_at = now

        # Check thresholds and alert
        _check_budget_thresholds(budget, tenant_id)

        db.commit()

    except Exception as exc:
        logger.error(f"Failed to update budget usage: {exc}", exc_info=True)


def _check_budget_thresholds(budget: AIBudget, tenant_id: str):
    """Check if budget thresholds exceeded and log alerts."""
    now = utc_now()

    # Daily threshold checks
    daily_percent = (budget.daily_usage_usd / budget.daily_limit_usd) * 100 if budget.daily_limit_usd > 0 else 0

    if daily_percent >= budget.critical_threshold_percent and not budget.daily_critical_sent:
        logger.critical(
            f"AI budget CRITICAL: Tenant {tenant_id} has used {daily_percent:.1f}% "
            f"(${budget.daily_usage_usd:.2f}/${budget.daily_limit_usd:.2f}) of daily limit"
        )
        budget.daily_critical_sent = now

    elif daily_percent >= budget.warning_threshold_percent and not budget.daily_warning_sent:
        logger.warning(
            f"AI budget WARNING: Tenant {tenant_id} has used {daily_percent:.1f}% "
            f"(${budget.daily_usage_usd:.2f}/${budget.daily_limit_usd:.2f}) of daily limit"
        )
        budget.daily_warning_sent = now

    # Monthly threshold checks
    monthly_percent = (budget.monthly_usage_usd / budget.monthly_limit_usd) * 100 if budget.monthly_limit_usd > 0 else 0

    if monthly_percent >= budget.critical_threshold_percent and not budget.monthly_critical_sent:
        logger.critical(
            f"AI budget CRITICAL: Tenant {tenant_id} has used {monthly_percent:.1f}% "
            f"(${budget.monthly_usage_usd:.2f}/${budget.monthly_limit_usd:.2f}) of monthly limit"
        )
        budget.monthly_critical_sent = now

    elif monthly_percent >= budget.warning_threshold_percent and not budget.monthly_warning_sent:
        logger.warning(
            f"AI budget WARNING: Tenant {tenant_id} has used {monthly_percent:.1f}% "
            f"(${budget.monthly_usage_usd:.2f}/${budget.monthly_limit_usd:.2f}) of monthly limit"
        )
        budget.monthly_warning_sent = now


def log_usage_from_analysis(
    db: Session,
    analysis: Dict[str, Any],
    tenant_id: str,
    document_id: Optional[int] = None,
    obligation_id: Optional[int] = None,
    user_id: Optional[str] = None,
    operation: Optional[str] = None,
) -> Optional[AIUsageLog]:
    """
    Log AI usage from an analysis payload (backward compatibility shim).

    Args:
        db: Database session
        analysis: Analysis response containing usage details
        tenant_id: Tenant ID
        document_id: Related document ID
        obligation_id: Related obligation ID
        user_id: User who triggered the request
        operation: Operation context

    Returns:
        Created AIUsageLog or None if no usage data
    """
    try:
        usage = analysis.get("usage") or {}
        if not usage:
            return None

        # Extract provider/model from analysis or use defaults
        provider = usage.get("provider", "openai")
        model = usage.get("model", "gpt-4")
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return log_usage(
            db=db,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tenant_id=tenant_id,
            operation=operation,
            document_id=document_id,
            obligation_id=obligation_id,
            user_id=user_id,
            request_metadata=usage.get("request_metadata"),
            response_metadata=usage.get("response_metadata"),
        )

    except Exception as exc:
        logger.debug(f"AI usage logging skipped: {exc}")
        return None

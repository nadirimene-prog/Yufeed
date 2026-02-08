"""
AI Cost Analytics Service.

Provides cost reporting and budget management for AI API usage.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.models.ai_usage_models import AIUsageLog, AIBudget


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class AICostService:
    """Service for AI cost analytics and budget management."""

    def __init__(self, db: Session):
        self.db = db

    def get_usage_summary(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Get AI usage summary for a tenant within a date range.

        Args:
            tenant_id: Tenant ID
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)

        Returns:
            Dict with usage statistics
        """
        if not start_date:
            start_date = utc_now() - timedelta(days=30)
        if not end_date:
            end_date = utc_now()

        # Query usage logs
        query = self.db.query(AIUsageLog).filter(
            and_(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.created_at >= start_date,
                AIUsageLog.created_at <= end_date,
            )
        )

        # Aggregate metrics
        total_calls = query.count()
        total_cost = (
            self.db.query(func.sum(AIUsageLog.estimated_cost_usd))
            .filter(
                and_(
                    AIUsageLog.tenant_id == tenant_id,
                    AIUsageLog.created_at >= start_date,
                    AIUsageLog.created_at <= end_date,
                )
            )
            .scalar()
            or 0.0
        )

        total_tokens = (
            self.db.query(func.sum(AIUsageLog.total_tokens))
            .filter(
                and_(
                    AIUsageLog.tenant_id == tenant_id,
                    AIUsageLog.created_at >= start_date,
                    AIUsageLog.created_at <= end_date,
                )
            )
            .scalar()
            or 0
        )

        # Breakdown by provider
        provider_breakdown = (
            self.db.query(
                AIUsageLog.provider,
                func.count(AIUsageLog.id).label("calls"),
                func.sum(AIUsageLog.estimated_cost_usd).label("cost"),
                func.sum(AIUsageLog.total_tokens).label("tokens"),
            )
            .filter(
                and_(
                    AIUsageLog.tenant_id == tenant_id,
                    AIUsageLog.created_at >= start_date,
                    AIUsageLog.created_at <= end_date,
                )
            )
            .group_by(AIUsageLog.provider)
            .all()
        )

        # Breakdown by model
        model_breakdown = (
            self.db.query(
                AIUsageLog.model,
                func.count(AIUsageLog.id).label("calls"),
                func.sum(AIUsageLog.estimated_cost_usd).label("cost"),
                func.sum(AIUsageLog.total_tokens).label("tokens"),
            )
            .filter(
                and_(
                    AIUsageLog.tenant_id == tenant_id,
                    AIUsageLog.created_at >= start_date,
                    AIUsageLog.created_at <= end_date,
                )
            )
            .group_by(AIUsageLog.model)
            .all()
        )

        # Breakdown by operation
        operation_breakdown = (
            self.db.query(
                AIUsageLog.operation,
                func.count(AIUsageLog.id).label("calls"),
                func.sum(AIUsageLog.estimated_cost_usd).label("cost"),
            )
            .filter(
                and_(
                    AIUsageLog.tenant_id == tenant_id,
                    AIUsageLog.created_at >= start_date,
                    AIUsageLog.created_at <= end_date,
                    AIUsageLog.operation.isnot(None),
                )
            )
            .group_by(AIUsageLog.operation)
            .all()
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_calls": total_calls,
                "total_cost_usd": round(total_cost, 2),
                "total_tokens": total_tokens,
                "avg_cost_per_call": round(total_cost / total_calls, 4) if total_calls > 0 else 0.0,
            },
            "by_provider": [
                {
                    "provider": row.provider,
                    "calls": row.calls,
                    "cost_usd": round(row.cost, 2),
                    "tokens": row.tokens,
                }
                for row in provider_breakdown
            ],
            "by_model": [
                {
                    "model": row.model,
                    "calls": row.calls,
                    "cost_usd": round(row.cost, 2),
                    "tokens": row.tokens,
                }
                for row in model_breakdown
            ],
            "by_operation": [
                {
                    "operation": row.operation,
                    "calls": row.calls,
                    "cost_usd": round(row.cost, 2),
                }
                for row in operation_breakdown
            ],
        }

    def get_daily_trend(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get daily cost trend for the past N days.

        Args:
            tenant_id: Tenant ID
            days: Number of days to include

        Returns:
            List of daily usage data
        """
        start_date = utc_now() - timedelta(days=days)

        # Query daily aggregates
        daily_data = (
            self.db.query(
                func.date(AIUsageLog.created_at).label("date"),
                func.count(AIUsageLog.id).label("calls"),
                func.sum(AIUsageLog.estimated_cost_usd).label("cost"),
                func.sum(AIUsageLog.total_tokens).label("tokens"),
            )
            .filter(
                and_(
                    AIUsageLog.tenant_id == tenant_id,
                    AIUsageLog.created_at >= start_date,
                )
            )
            .group_by(func.date(AIUsageLog.created_at))
            .order_by(func.date(AIUsageLog.created_at))
            .all()
        )

        return [
            {
                "date": row.date.isoformat(),
                "calls": row.calls,
                "cost_usd": round(row.cost, 2),
                "tokens": row.tokens,
            }
            for row in daily_data
        ]

    def get_budget_status(self, tenant_id: str) -> Dict:
        """
        Get current budget status for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Budget status with usage percentages
        """
        budget = self.db.query(AIBudget).filter(AIBudget.tenant_id == tenant_id).first()

        if not budget:
            return {
                "exists": False,
                "message": "No budget configured for this tenant",
            }

        daily_percent = (
            (budget.daily_usage_usd / budget.daily_limit_usd) * 100
            if budget.daily_limit_usd > 0
            else 0
        )
        monthly_percent = (
            (budget.monthly_usage_usd / budget.monthly_limit_usd) * 100
            if budget.monthly_limit_usd > 0
            else 0
        )

        return {
            "exists": True,
            "daily": {
                "limit_usd": budget.daily_limit_usd,
                "usage_usd": round(budget.daily_usage_usd, 2),
                "remaining_usd": round(budget.daily_limit_usd - budget.daily_usage_usd, 2),
                "usage_percent": round(daily_percent, 1),
                "reset_at": budget.daily_reset_at.isoformat(),
            },
            "monthly": {
                "limit_usd": budget.monthly_limit_usd,
                "usage_usd": round(budget.monthly_usage_usd, 2),
                "remaining_usd": round(budget.monthly_limit_usd - budget.monthly_usage_usd, 2),
                "usage_percent": round(monthly_percent, 1),
                "reset_at": budget.monthly_reset_at.isoformat(),
            },
            "thresholds": {
                "warning_percent": budget.warning_threshold_percent,
                "critical_percent": budget.critical_threshold_percent,
            },
        }

    def update_budget(
        self,
        tenant_id: str,
        daily_limit_usd: Optional[float] = None,
        monthly_limit_usd: Optional[float] = None,
        warning_threshold_percent: Optional[int] = None,
        critical_threshold_percent: Optional[int] = None,
    ) -> AIBudget:
        """
        Update budget limits for a tenant.

        Args:
            tenant_id: Tenant ID
            daily_limit_usd: Daily budget limit
            monthly_limit_usd: Monthly budget limit
            warning_threshold_percent: Warning threshold percentage
            critical_threshold_percent: Critical threshold percentage

        Returns:
            Updated AIBudget
        """
        budget = self.db.query(AIBudget).filter(AIBudget.tenant_id == tenant_id).first()

        if not budget:
            # Create new budget
            budget = AIBudget(
                tenant_id=tenant_id,
                daily_limit_usd=daily_limit_usd or 100.0,
                monthly_limit_usd=monthly_limit_usd or 3000.0,
                warning_threshold_percent=warning_threshold_percent or 80,
                critical_threshold_percent=critical_threshold_percent or 95,
                daily_reset_at=utc_now(),
                monthly_reset_at=utc_now(),
            )
            self.db.add(budget)
        else:
            # Update existing budget
            if daily_limit_usd is not None:
                budget.daily_limit_usd = daily_limit_usd
            if monthly_limit_usd is not None:
                budget.monthly_limit_usd = monthly_limit_usd
            if warning_threshold_percent is not None:
                budget.warning_threshold_percent = warning_threshold_percent
            if critical_threshold_percent is not None:
                budget.critical_threshold_percent = critical_threshold_percent

        self.db.commit()
        self.db.refresh(budget)

        return budget

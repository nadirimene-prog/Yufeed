"""
AI Cost Monitoring API.

Endpoints for viewing AI usage costs and managing budgets.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from src.database import get_db
from src.auth.dependencies import CurrentUser, require_any_role, require_role
from src.tenancy.context import get_current_tenant
from src.services.ai_cost_service import AICostService
from pydantic import BaseModel

router = APIRouter(
    prefix="/ai-costs",
    tags=["ai-costs"],
    dependencies=[Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer"]))],
)


class BudgetUpdate(BaseModel):
    """Budget update request."""

    daily_limit_usd: Optional[float] = None
    monthly_limit_usd: Optional[float] = None
    warning_threshold_percent: Optional[int] = None
    critical_threshold_percent: Optional[int] = None


@router.get("/usage-summary")
def get_usage_summary(
    days: int = Query(30, description="Number of days to include", ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Get AI usage summary for the current tenant.

    Returns aggregated costs, token usage, and breakdowns by provider/model/operation.
    """
    tenant_id = get_current_tenant()
    service = AICostService(db)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    summary = service.get_usage_summary(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )
    if isinstance(summary, dict) and "tracking_status" not in summary:
        summary["tracking_status"] = "full"
    return summary


@router.get("/daily-trend")
def get_daily_trend(
    days: int = Query(30, description="Number of days to include", ge=1, le=90),
    db: Session = Depends(get_db),
):
    """
    Get daily cost trend for the current tenant.

    Returns daily usage data for visualization.
    """
    tenant_id = get_current_tenant()
    service = AICostService(db)

    return service.get_daily_trend(tenant_id=tenant_id, days=days)


@router.get("/budget")
def get_budget_status(db: Session = Depends(get_db)):
    """
    Get current budget status for the tenant.

    Shows daily/monthly limits, usage, and thresholds.
    """
    tenant_id = get_current_tenant()
    service = AICostService(db)

    return service.get_budget_status(tenant_id=tenant_id)


@router.put("/budget")
def update_budget(
    budget_update: BudgetUpdate,
    _current_user: CurrentUser = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Update budget limits for the tenant.

    Requires admin privileges.
    """
    tenant_id = get_current_tenant()
    service = AICostService(db)

    budget = service.update_budget(
        tenant_id=tenant_id,
        daily_limit_usd=budget_update.daily_limit_usd,
        monthly_limit_usd=budget_update.monthly_limit_usd,
        warning_threshold_percent=budget_update.warning_threshold_percent,
        critical_threshold_percent=budget_update.critical_threshold_percent,
    )

    return {
        "message": "Budget updated successfully",
        "budget": {
            "daily_limit_usd": budget.daily_limit_usd,
            "monthly_limit_usd": budget.monthly_limit_usd,
            "warning_threshold_percent": budget.warning_threshold_percent,
            "critical_threshold_percent": budget.critical_threshold_percent,
        },
    }

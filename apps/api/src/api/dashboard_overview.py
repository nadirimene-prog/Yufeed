"""
Dashboard Overview API
Unified aggregation contract for the v2 frontend dashboard hub.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser, require_any_role
from src.config import settings
from src.database import get_db
from src.models.transaction_models import Alert, Case, Transaction


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DashboardView = Literal["operations", "compliance", "monitoring"]
DashboardTimeRange = Literal["24h", "7d", "30d"]


def _parse_time_range(value: DashboardTimeRange) -> timedelta:
    mapping = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    return mapping[value]


def _float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


@router.get("/overview")
def get_dashboard_overview(
    view: DashboardView = Query("operations"),
    time_range: DashboardTimeRange = Query("7d"),
    limit: int = Query(12, ge=5, le=50),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"])),
):
    """
    Return a unified dashboard payload for operations/compliance/monitoring views.
    """
    if not settings.DASHBOARD_V2_ENABLED:
        raise HTTPException(status_code=503, detail="Dashboard v2 is currently disabled")

    now = utc_now()
    start = now - _parse_time_range(time_range)

    # KPI aggregates
    pending_alerts = db.query(func.count(Alert.id)).filter(Alert.status == "pending").scalar() or 0
    critical_alerts = (
        db.query(func.count(Alert.id)).filter(Alert.severity == "critical").scalar() or 0
    )
    open_cases = (
        db.query(func.count(Case.id)).filter(Case.status.in_(["open", "in_progress"])).scalar() or 0
    )
    transactions_in_range = (
        db.query(func.count(Transaction.id)).filter(Transaction.timestamp >= start).scalar() or 0
    )
    avg_risk_score = (
        db.query(func.avg(Transaction.risk_score))
        .filter(and_(Transaction.timestamp >= start, Transaction.risk_score.isnot(None)))
        .scalar()
    )

    # Alert queue (prioritized)
    alert_rows = (
        db.query(Alert)
        .filter(and_(Alert.created_at >= start, Alert.status.in_(["pending", "in_review"])))
        .order_by(Alert.priority.asc(), Alert.created_at.desc())
        .limit(limit)
        .all()
    )

    alerts = [
        {
            "id": row.id,
            "alert_id": row.alert_id,
            "alert_type": row.alert_type,
            "severity": row.severity,
            "status": row.status,
            "priority": row.priority,
            "user_id": row.user_id,
            "risk_score": _float(row.risk_score),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in alert_rows
    ]

    # Active cases
    case_rows = (
        db.query(Case)
        .filter(Case.status.in_(["open", "in_progress"]))
        .order_by(Case.updated_at.desc(), Case.opened_at.desc())
        .limit(limit)
        .all()
    )
    cases = [
        {
            "id": row.id,
            "case_id": row.case_id,
            "title": row.title or row.case_id,
            "status": row.status,
            "priority": row.priority,
            "assigned_to": row.assigned_to,
            "opened_at": row.opened_at.isoformat() if row.opened_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in case_rows
    ]

    # Health snapshot
    one_day_ago = now - timedelta(hours=24)
    stuck_alerts = (
        db.query(func.count(Alert.id))
        .filter(and_(Alert.status == "pending", Alert.created_at < one_day_ago))
        .scalar()
        or 0
    )
    unprocessed_transactions = (
        db.query(func.count(Transaction.id)).filter(Transaction.risk_score.is_(None)).scalar() or 0
    )

    if stuck_alerts > 100 or unprocessed_transactions > 1000:
        health_status = "degraded"
    elif stuck_alerts > 0 or unprocessed_transactions > 0:
        health_status = "warning"
    else:
        health_status = "healthy"

    return {
        "view": view,
        "time_range": time_range,
        "generated_at": now.isoformat(),
        "kpis": {
            "pending_alerts": pending_alerts,
            "critical_alerts": critical_alerts,
            "open_cases": open_cases,
            "transactions_in_range": transactions_in_range,
            "average_risk_score": round(_float(avg_risk_score), 2),
        },
        "badges": {
            "alerts_pending": pending_alerts,
            "cases_open": open_cases,
            "critical_open": critical_alerts,
        },
        "system_health": {
            "status": health_status,
            "stuck_alerts": stuck_alerts,
            "unprocessed_transactions": unprocessed_transactions,
        },
        "queues": {
            "alerts": alerts,
            "cases": cases,
        },
    }

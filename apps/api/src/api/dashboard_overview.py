"""
Dashboard Overview API
Unified aggregation contract for the v2 frontend dashboard hub.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser, require_any_role
from src.config import settings
from src.database import get_db
from src.models.case_decision import CaseDecision
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


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(median(values)), 2)


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

    critical_bar = {
        "p1_sla_breaches": 0,
        "p2_sla_breaches": 0,
        "sanctions_hits_unreviewed": 0,
        "sar_due_24h": 0,
        "high_risk_cases_unassigned": 0,
        "ingestion_lag_minutes": 0,
    }
    queue_summary = {
        "alerts_open": pending_alerts,
        "cases_open": open_cases,
        "approvals_pending": 0,
        "reg_tasks_due": 0,
    }
    governance = {
        "rule_drift_score": 0.0,
        "alert_to_case_rate": 0.0,
        "fp_proxy_rate": 0.0,
        "audit_completeness_rate": 0.0,
    }
    throughput = {
        "median_time_to_first_action_minutes": 0.0,
        "median_case_resolution_hours": 0.0,
    }

    if settings.DASHBOARD_AMLCO_V3_ENABLED:
        p1_threshold = now - timedelta(hours=2)
        p2_threshold = now - timedelta(hours=8)
        critical_bar["p1_sla_breaches"] = (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    Alert.status.in_(["pending", "in_review"]),
                    Alert.created_at < p1_threshold,
                    or_(Alert.priority == 1, Alert.severity == "critical"),
                )
            )
            .scalar()
            or 0
        )
        critical_bar["p2_sla_breaches"] = (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    Alert.status.in_(["pending", "in_review"]),
                    Alert.created_at < p2_threshold,
                    Alert.severity.in_(["high", "medium"]),
                )
            )
            .scalar()
            or 0
        )
        critical_bar["sanctions_hits_unreviewed"] = (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    Alert.status.in_(["pending", "in_review"]),
                    or_(
                        Alert.alert_type.ilike("%sanction%"),
                        Alert.alert_type.ilike("%pep%"),
                    ),
                )
            )
            .scalar()
            or 0
        )
        critical_bar["sar_due_24h"] = (
            db.query(func.count(Case.id))
            .filter(
                and_(
                    Case.status.in_(["open", "in_progress"]),
                    Case.outcome == "sar_required",
                    Case.opened_at <= now - timedelta(hours=48),
                    Case.opened_at > now - timedelta(hours=72),
                )
            )
            .scalar()
            or 0
        )
        critical_bar["high_risk_cases_unassigned"] = (
            db.query(func.count(Case.id))
            .filter(
                and_(
                    Case.status.in_(["open", "in_progress"]),
                    Case.priority.in_(["high", "critical", "urgent", "p1"]),
                    or_(Case.assigned_to.is_(None), Case.assigned_to == ""),
                )
            )
            .scalar()
            or 0
        )
        latest_transaction_ts = db.query(func.max(Transaction.timestamp)).scalar()
        latest_transaction_ts = _as_utc(latest_transaction_ts)
        critical_bar["ingestion_lag_minutes"] = (
            max(0, int((now - latest_transaction_ts).total_seconds() // 60))
            if latest_transaction_ts
            else 0
        )

        queue_summary["approvals_pending"] = (
            db.query(func.count(CaseDecision.id))
            .filter(CaseDecision.status == "submitted")
            .scalar()
            or 0
        )
        queue_summary["reg_tasks_due"] = (
            db.query(func.count(Case.id))
            .filter(and_(Case.status.in_(["open", "in_progress"]), Case.outcome == "sar_required"))
            .scalar()
            or 0
        )

        resolved_alert_total = (
            db.query(func.count(Alert.id))
            .filter(and_(Alert.status == "resolved", Alert.created_at >= start))
            .scalar()
            or 0
        )
        resolved_alert_false_positive = (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    Alert.status == "resolved",
                    Alert.created_at >= start,
                    Alert.resolution_status.in_(["false_positive", "dismissed"]),
                )
            )
            .scalar()
            or 0
        )
        high_pressure_alerts = (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    Alert.status.in_(["pending", "in_review"]),
                    Alert.severity.in_(["high", "critical"]),
                )
            )
            .scalar()
            or 0
        )

        closed_cases = (
            db.query(Case)
            .filter(
                and_(
                    Case.status == "closed", Case.closed_at.isnot(None), Case.opened_at.isnot(None)
                )
            )
            .all()
        )
        audit_complete = [
            case
            for case in closed_cases
            if (case.outcome or "").strip() and (case.outcome_notes or "").strip()
        ]
        governance["rule_drift_score"] = min(
            100.0, round(high_pressure_alerts / max(pending_alerts, 1) * 100, 2)
        )
        governance["alert_to_case_rate"] = round(
            open_cases / max(pending_alerts + open_cases, 1), 4
        )
        governance["fp_proxy_rate"] = round(
            resolved_alert_false_positive / max(resolved_alert_total, 1), 4
        )
        governance["audit_completeness_rate"] = round(
            len(audit_complete) / max(len(closed_cases), 1), 4
        )

        actionable_alerts = (
            db.query(Alert)
            .filter(and_(Alert.created_at >= start, Alert.updated_at.isnot(None)))
            .all()
        )
        first_action_latencies: list[float] = []
        for alert in actionable_alerts:
            created_at = _as_utc(alert.created_at)
            updated_at = _as_utc(alert.updated_at)
            if not created_at or not updated_at:
                continue
            delta = (updated_at - created_at).total_seconds() / 60
            if delta >= 0:
                first_action_latencies.append(delta)

        case_resolution_hours: list[float] = []
        for case in closed_cases:
            opened_at = _as_utc(case.opened_at)
            closed_at = _as_utc(case.closed_at)
            if not opened_at or not closed_at:
                continue
            delta = (closed_at - opened_at).total_seconds() / 3600
            if delta >= 0:
                case_resolution_hours.append(delta)

        throughput["median_time_to_first_action_minutes"] = _median(first_action_latencies)
        throughput["median_case_resolution_hours"] = _median(case_resolution_hours)

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
        "critical_bar": critical_bar,
        "queue_summary": queue_summary,
        "governance": governance,
        "throughput": throughput,
    }

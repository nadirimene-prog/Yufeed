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
SAR_DEADLINE_HOURS = 72


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


def _bucket_ranges(
    start: datetime, end: datetime, points: int = 7
) -> list[tuple[datetime, datetime]]:
    if points <= 0 or end <= start:
        return []
    total_seconds = max(1, int((end - start).total_seconds()))
    bucket_seconds = max(1, total_seconds // points)
    buckets: list[tuple[datetime, datetime]] = []
    cursor = start
    for index in range(points):
        bucket_end = (
            end if index == points - 1 else min(end, cursor + timedelta(seconds=bucket_seconds))
        )
        buckets.append((cursor, bucket_end))
        cursor = bucket_end
    return buckets


def _throughput_window_metrics(db: Session, start: datetime, end: datetime) -> dict[str, float]:
    actionable_alerts = (
        db.query(Alert)
        .filter(
            and_(
                Alert.created_at >= start,
                Alert.created_at < end,
                Alert.updated_at.isnot(None),
            )
        )
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

    closed_cases = (
        db.query(Case)
        .filter(
            and_(
                Case.status == "closed",
                Case.closed_at.isnot(None),
                Case.opened_at.isnot(None),
                Case.closed_at >= start,
                Case.closed_at < end,
            )
        )
        .all()
    )
    case_resolution_hours: list[float] = []
    for case in closed_cases:
        opened_at = _as_utc(case.opened_at)
        closed_at = _as_utc(case.closed_at)
        if not opened_at or not closed_at:
            continue
        delta = (closed_at - opened_at).total_seconds() / 3600
        if delta >= 0:
            case_resolution_hours.append(delta)

    return {
        "median_time_to_first_action_minutes": _median(first_action_latencies),
        "median_case_resolution_hours": _median(case_resolution_hours),
    }


def _freshness_meta(
    *,
    generated_at: datetime,
    stale_after_seconds: int,
    source_watermark_at: datetime | None = None,
) -> dict[str, object]:
    source_lag_seconds = (
        max(0, int((generated_at - source_watermark_at).total_seconds()))
        if source_watermark_at is not None
        else None
    )
    return {
        "generated_at": generated_at.isoformat(),
        "stale_after_seconds": stale_after_seconds,
        "source_watermark_at": source_watermark_at.isoformat() if source_watermark_at else None,
        "source_lag_seconds": source_lag_seconds,
    }


def _alert_open_as_of_filter(as_of: datetime):
    return and_(
        Alert.created_at.isnot(None),
        Alert.created_at <= as_of,
        or_(Alert.resolved_at.is_(None), Alert.resolved_at > as_of),
    )


def _case_open_as_of_filter(as_of: datetime):
    return and_(
        Case.opened_at.isnot(None),
        Case.opened_at <= as_of,
        or_(Case.closed_at.is_(None), Case.closed_at > as_of),
    )


def _decision_pending_as_of_filter(as_of: datetime):
    submitted_at = func.coalesce(CaseDecision.submitted_at, CaseDecision.created_at)
    return and_(
        submitted_at.isnot(None),
        submitted_at <= as_of,
        or_(CaseDecision.approved_at.is_(None), CaseDecision.approved_at > as_of),
    )


def _sar_due_within_24h_count(db: Session, *, as_of: datetime) -> int:
    due_by = as_of + timedelta(hours=24)
    candidates = (
        db.query(Case.opened_at)
        .filter(
            and_(
                _case_open_as_of_filter(as_of),
                Case.outcome == "sar_required",
                Case.opened_at > as_of - timedelta(hours=SAR_DEADLINE_HOURS),
                Case.opened_at <= as_of,
            )
        )
        .all()
    )
    count = 0
    for (opened_at,) in candidates:
        opened = _as_utc(opened_at)
        if not opened:
            continue
        due_at = opened + timedelta(hours=SAR_DEADLINE_HOURS)
        if as_of <= due_at <= due_by:
            count += 1
    return count


def _queue_summary_snapshot(db: Session, *, as_of: datetime) -> dict[str, int]:
    return {
        "alerts_open": (
            db.query(func.count(Alert.id)).filter(_alert_open_as_of_filter(as_of)).scalar() or 0
        ),
        "cases_open": (
            db.query(func.count(Case.id)).filter(_case_open_as_of_filter(as_of)).scalar() or 0
        ),
        "approvals_pending": (
            db.query(func.count(CaseDecision.id))
            .filter(_decision_pending_as_of_filter(as_of))
            .scalar()
            or 0
        ),
        "reg_tasks_due": (
            db.query(func.count(Case.id))
            .filter(and_(_case_open_as_of_filter(as_of), Case.outcome == "sar_required"))
            .scalar()
            or 0
        ),
    }


def _critical_bar_snapshot(
    db: Session, *, as_of: datetime, latest_transaction_ts: datetime | None
) -> dict[str, int]:
    p1_threshold = as_of - timedelta(hours=2)
    p2_threshold = as_of - timedelta(hours=8)
    unresolved_alert_as_of = _alert_open_as_of_filter(as_of)
    return {
        "p1_sla_breaches": (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    unresolved_alert_as_of,
                    Alert.created_at < p1_threshold,
                    or_(Alert.priority == 1, Alert.severity == "critical"),
                )
            )
            .scalar()
            or 0
        ),
        "p2_sla_breaches": (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    unresolved_alert_as_of,
                    Alert.created_at < p2_threshold,
                    Alert.severity.in_(["high", "medium"]),
                )
            )
            .scalar()
            or 0
        ),
        "sanctions_hits_unreviewed": (
            db.query(func.count(Alert.id))
            .filter(
                and_(
                    unresolved_alert_as_of,
                    or_(Alert.alert_type.ilike("%sanction%"), Alert.alert_type.ilike("%pep%")),
                )
            )
            .scalar()
            or 0
        ),
        "sar_due_24h": _sar_due_within_24h_count(db, as_of=as_of),
        "high_risk_cases_unassigned": (
            db.query(func.count(Case.id))
            .filter(
                and_(
                    _case_open_as_of_filter(as_of),
                    Case.priority.in_(["high", "critical", "urgent", "p1"]),
                    or_(Case.assigned_to.is_(None), Case.assigned_to == ""),
                )
            )
            .scalar()
            or 0
        ),
        "ingestion_lag_minutes": (
            max(0, int((as_of - latest_transaction_ts).total_seconds() // 60))
            if latest_transaction_ts
            else 0
        ),
    }


def _governance_snapshot(
    db: Session, *, window_start: datetime, as_of: datetime
) -> dict[str, float]:
    pending_alerts = (
        db.query(func.count(Alert.id)).filter(_alert_open_as_of_filter(as_of)).scalar() or 0
    )
    open_cases = db.query(func.count(Case.id)).filter(_case_open_as_of_filter(as_of)).scalar() or 0
    high_pressure_alerts = (
        db.query(func.count(Alert.id))
        .filter(and_(_alert_open_as_of_filter(as_of), Alert.severity.in_(["high", "critical"])))
        .scalar()
        or 0
    )
    resolved_alert_total = (
        db.query(func.count(Alert.id))
        .filter(
            and_(
                Alert.resolved_at.isnot(None),
                Alert.resolved_at >= window_start,
                Alert.resolved_at < as_of,
            )
        )
        .scalar()
        or 0
    )
    resolved_alert_false_positive = (
        db.query(func.count(Alert.id))
        .filter(
            and_(
                Alert.resolved_at.isnot(None),
                Alert.resolved_at >= window_start,
                Alert.resolved_at < as_of,
                Alert.resolution_status.in_(["false_positive", "dismissed"]),
            )
        )
        .scalar()
        or 0
    )
    closed_cases = (
        db.query(Case)
        .filter(
            and_(
                Case.closed_at.isnot(None),
                Case.opened_at.isnot(None),
                Case.closed_at >= window_start,
                Case.closed_at < as_of,
            )
        )
        .all()
    )
    audit_complete = [
        case
        for case in closed_cases
        if (case.outcome or "").strip() and (case.outcome_notes or "").strip()
    ]
    return {
        "rule_drift_score": min(
            100.0, round(high_pressure_alerts / max(pending_alerts, 1) * 100, 2)
        ),
        "alert_to_case_rate": round(open_cases / max(pending_alerts + open_cases, 1), 4),
        "fp_proxy_rate": round(resolved_alert_false_positive / max(resolved_alert_total, 1), 4),
        "audit_completeness_rate": round(len(audit_complete) / max(len(closed_cases), 1), 4),
    }


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
    window_delta = _parse_time_range(time_range)
    start = now - window_delta
    previous_start = start - window_delta

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

    latest_transaction_ts = db.query(func.max(Transaction.timestamp)).scalar()
    latest_transaction_ts = _as_utc(latest_transaction_ts)

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
        "median_time_to_first_action_delta_minutes": None,
        "median_case_resolution_delta_hours": None,
        "median_time_to_first_action_history": None,
        "median_case_resolution_history": None,
    }
    queue_summary_previous = None
    critical_bar_previous = None

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
        critical_bar["sar_due_24h"] = _sar_due_within_24h_count(db, as_of=now)
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

        current_throughput = _throughput_window_metrics(db, start, now)
        previous_throughput = _throughput_window_metrics(db, previous_start, start)
        throughput["median_time_to_first_action_minutes"] = current_throughput[
            "median_time_to_first_action_minutes"
        ]
        throughput["median_case_resolution_hours"] = current_throughput[
            "median_case_resolution_hours"
        ]
        throughput["median_time_to_first_action_delta_minutes"] = round(
            current_throughput["median_time_to_first_action_minutes"]
            - previous_throughput["median_time_to_first_action_minutes"],
            2,
        )
        throughput["median_case_resolution_delta_hours"] = round(
            current_throughput["median_case_resolution_hours"]
            - previous_throughput["median_case_resolution_hours"],
            2,
        )

        buckets = _bucket_ranges(start, now, 7)
        if buckets:
            throughput["median_time_to_first_action_history"] = [
                _throughput_window_metrics(db, bucket_start, bucket_end)[
                    "median_time_to_first_action_minutes"
                ]
                for bucket_start, bucket_end in buckets
            ]
            throughput["median_case_resolution_history"] = [
                _throughput_window_metrics(db, bucket_start, bucket_end)[
                    "median_case_resolution_hours"
                ]
                for bucket_start, bucket_end in buckets
            ]

        governance.update(_governance_snapshot(db, window_start=start, as_of=now))
        governance_buckets = _bucket_ranges(start, now, 7)
        if governance_buckets:
            governance_snapshots = [
                _governance_snapshot(db, window_start=bucket_start, as_of=bucket_end)
                for bucket_start, bucket_end in governance_buckets
            ]
            governance["rule_drift_score_history"] = [
                snapshot["rule_drift_score"] for snapshot in governance_snapshots
            ]
            governance["alert_to_case_rate_history"] = [
                snapshot["alert_to_case_rate"] for snapshot in governance_snapshots
            ]
            governance["fp_proxy_rate_history"] = [
                snapshot["fp_proxy_rate"] for snapshot in governance_snapshots
            ]
            governance["audit_completeness_rate_history"] = [
                snapshot["audit_completeness_rate"] for snapshot in governance_snapshots
            ]

        critical_bar = _critical_bar_snapshot(
            db,
            as_of=now,
            latest_transaction_ts=latest_transaction_ts,
        )
        queue_summary = _queue_summary_snapshot(db, as_of=now)

        previous_latest_transaction_ts = _as_utc(
            db.query(func.max(Transaction.timestamp))
            .filter(Transaction.timestamp <= start)
            .scalar()
        )
        critical_bar_previous = _critical_bar_snapshot(
            db,
            as_of=start,
            latest_transaction_ts=previous_latest_transaction_ts,
        )
        queue_summary_previous = _queue_summary_snapshot(db, as_of=start)

    return {
        "view": view,
        "time_range": time_range,
        "generated_at": now.isoformat(),
        "freshness": _freshness_meta(
            generated_at=now,
            stale_after_seconds=120,
            source_watermark_at=latest_transaction_ts,
        ),
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
        "queue_summary_previous": queue_summary_previous,
        "critical_bar_previous": critical_bar_previous,
        "governance": governance,
        "throughput": throughput,
    }

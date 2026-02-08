"""
Monitoring Dashboard API
Provides comprehensive dashboard data for transaction monitoring.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from typing import List
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from src.database import get_db
from src.models.transaction_models import Transaction, Alert, Case, MonitoringRule, UserRiskProfile
from src.schemas.transaction_schemas import (
    AlertStatistics,
    TransactionStatistics,
    MonitoringDashboard,
    AlertResponse,
    UserRiskProfileResponse,
    CaseResponse,
    MonitoringRuleResponse,
)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring-dashboard"])


@router.get("/dashboard", response_model=MonitoringDashboard)
def get_monitoring_dashboard(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """
    Get comprehensive monitoring dashboard data.

    Includes:
    - Alert statistics
    - Transaction statistics
    - Top risk users
    - Recent alerts
    - Active cases
    - Rule performance
    """
    start_date = utc_now() - timedelta(days=days)

    # Get alert statistics
    alert_stats = _get_alert_statistics(db, start_date)

    # Get transaction statistics
    transaction_stats = _get_transaction_statistics(db, start_date)

    # Get top risk users (top 10)
    top_risk_users = (
        db.query(UserRiskProfile)
        .filter(UserRiskProfile.risk_level.in_(["high", "critical"]))
        .order_by(UserRiskProfile.overall_risk_score.desc())
        .limit(10)
        .all()
    )

    # Get recent alerts (last 20)
    recent_alerts = (
        db.query(Alert)
        .filter(Alert.created_at >= start_date)
        .order_by(Alert.created_at.desc())
        .limit(20)
        .all()
    )

    # Get active cases
    active_cases = (
        db.query(Case)
        .filter(Case.status.in_(["open", "in_progress"]))
        .order_by(Case.priority.desc(), Case.opened_at.desc())
        .limit(10)
        .all()
    )

    # Get rule performance (rules with most alerts)
    rule_performance = (
        db.query(MonitoringRule)
        .filter(MonitoringRule.enabled == True)
        .order_by(MonitoringRule.alert_count.desc())
        .limit(10)
        .all()
    )

    return MonitoringDashboard(
        alert_stats=alert_stats,
        transaction_stats=transaction_stats,
        top_risk_users=top_risk_users,
        recent_alerts=recent_alerts,
        active_cases=active_cases,
        rule_performance=rule_performance,
    )


@router.get("/metrics/realtime")
def get_realtime_metrics(db: Session = Depends(get_db)):
    """
    Get real-time monitoring metrics for dashboard.

    Updated every minute for live monitoring.
    """
    # Last hour stats
    one_hour_ago = utc_now() - timedelta(hours=1)

    # Transactions in last hour
    txn_count_1h = (
        db.query(func.count(Transaction.id)).filter(Transaction.timestamp >= one_hour_ago).scalar()
        or 0
    )

    # Alerts in last hour
    alert_count_1h = (
        db.query(func.count(Alert.id)).filter(Alert.created_at >= one_hour_ago).scalar() or 0
    )

    # Critical alerts pending
    critical_pending = (
        db.query(func.count(Alert.id))
        .filter(and_(Alert.severity == "critical", Alert.status == "pending"))
        .scalar()
        or 0
    )

    # High-risk transactions in last hour
    high_risk_1h = (
        db.query(func.count(Transaction.id))
        .filter(
            and_(
                Transaction.timestamp >= one_hour_ago,
                Transaction.risk_level.in_(["high", "critical"]),
            )
        )
        .scalar()
        or 0
    )

    # Average processing time (placeholder - would need processing_time field)
    # For now, return mock data
    avg_processing_time_ms = 250

    return {
        "timestamp": utc_now().isoformat(),
        "transactions_last_hour": txn_count_1h,
        "alerts_last_hour": alert_count_1h,
        "critical_alerts_pending": critical_pending,
        "high_risk_transactions_last_hour": high_risk_1h,
        "average_processing_time_ms": avg_processing_time_ms,
        "system_status": "operational",
    }


@router.get("/trends/alerts")
def get_alert_trends(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """
    Get alert trends over time for dashboard charts.

    Returns daily alert counts by severity.
    """
    start_date = utc_now() - timedelta(days=days)

    # Get daily alert counts
    from sqlalchemy import cast, Date

    dialect = db.get_bind().dialect.name if db.get_bind() else ""
    date_expr = func.date(Alert.created_at) if dialect == "sqlite" else cast(Alert.created_at, Date)

    daily_alerts = (
        db.query(date_expr.label("date"), Alert.severity, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(date_expr, Alert.severity)
        .order_by("date")
        .all()
    )

    # Format for chart
    trends = {}
    for date, severity, count in daily_alerts:
        date_str = date.isoformat() if hasattr(date, "isoformat") else str(date)
        if date_str not in trends:
            trends[date_str] = {
                "date": date_str,
                "low": 0,
                "medium": 0,
                "high": 0,
                "critical": 0,
                "total": 0,
            }
        trends[date_str][severity] = count
        trends[date_str]["total"] += count

    return {"period_days": days, "trends": list(trends.values())}


@router.get("/trends/transactions")
def get_transaction_trends(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """
    Get transaction trends over time for dashboard charts.

    Returns daily transaction counts and volumes.
    """
    start_date = utc_now() - timedelta(days=days)

    from sqlalchemy import cast, Date

    daily_transactions = (
        db.query(
            (
                func.date(Transaction.timestamp)
                if (db.get_bind().dialect.name if db.get_bind() else "") == "sqlite"
                else cast(Transaction.timestamp, Date)
            ).label("date"),
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.amount).label("volume"),
            func.avg(Transaction.amount).label("avg_amount"),
        )
        .filter(Transaction.timestamp >= start_date)
        .group_by("date")
        .order_by("date")
        .all()
    )

    trends = []
    for date, count, volume, avg_amount in daily_transactions:
        trends.append(
            {
                "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
                "transaction_count": count,
                "total_volume": float(volume or 0),
                "average_amount": float(avg_amount or 0),
            }
        )

    return {"period_days": days, "trends": trends}


@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    """
    Get system health status for monitoring.
    """
    # Check database connectivity (already done by getting session)

    # Count enabled rules
    enabled_rules = (
        db.query(func.count(MonitoringRule.id)).filter(MonitoringRule.enabled == True).scalar() or 0
    )

    # Check for stuck alerts (pending for >24 hours)
    yesterday = utc_now() - timedelta(hours=24)
    stuck_alerts = (
        db.query(func.count(Alert.id))
        .filter(and_(Alert.status == "pending", Alert.created_at < yesterday))
        .scalar()
        or 0
    )

    # Check for processing backlog (transactions without risk scores)
    unprocessed_txns = (
        db.query(func.count(Transaction.id)).filter(Transaction.risk_score.is_(None)).scalar() or 0
    )

    # Determine overall health
    if stuck_alerts > 100 or unprocessed_txns > 1000:
        status = "degraded"
    elif stuck_alerts > 0 or unprocessed_txns > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "status": status,
        "timestamp": utc_now().isoformat(),
        "checks": {
            "database": "connected",
            "enabled_rules": enabled_rules,
            "stuck_alerts": stuck_alerts,
            "unprocessed_transactions": unprocessed_txns,
        },
        "recommendations": _get_health_recommendations(stuck_alerts, unprocessed_txns),
    }


@router.get("/compliance-coverage")
def get_compliance_coverage(db: Session = Depends(get_db)):
    """
    Get compliance coverage statistics.

    Shows which regulations have monitoring rules linked.
    """
    # Count rules with regulatory linkage
    rules_with_regs = (
        db.query(func.count(MonitoringRule.id))
        .filter(MonitoringRule.regulatory_source_id.isnot(None))
        .scalar()
        or 0
    )

    total_rules = db.query(func.count(MonitoringRule.id)).scalar() or 0

    coverage_percent = (rules_with_regs / total_rules * 100) if total_rules > 0 else 0

    # Get rules by category
    category_coverage = (
        db.query(
            MonitoringRule.category,
            func.count(MonitoringRule.id).label("total"),
            func.sum(case((MonitoringRule.regulatory_source_id.isnot(None), 1), else_=0)).label(
                "with_regulations"
            ),
        )
        .group_by(MonitoringRule.category)
        .all()
    )

    categories = []
    for category, total, with_regs in category_coverage:
        categories.append(
            {
                "category": category or "uncategorized",
                "total_rules": total,
                "rules_with_regulations": with_regs,
                "coverage_percent": (with_regs / total * 100) if total > 0 else 0,
            }
        )

    return {
        "overall_coverage_percent": coverage_percent,
        "rules_with_regulations": rules_with_regs,
        "total_rules": total_rules,
        "category_breakdown": categories,
    }


# ============================================================================
# Helper Functions
# ============================================================================


def _get_alert_statistics(db: Session, start_date: datetime) -> AlertStatistics:
    """Get alert statistics for dashboard."""
    # Total alerts
    total_alerts = (
        db.query(func.count(Alert.id)).filter(Alert.created_at >= start_date).scalar() or 0
    )

    # Alerts by status
    status_results = (
        db.query(Alert.status, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(Alert.status)
        .all()
    )

    alerts_by_status = {row.status: row.count for row in status_results}

    severity_results = (
        db.query(Alert.severity, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(Alert.severity)
        .all()
    )

    alerts_by_severity = {row.severity: row.count for row in severity_results}

    pending_alerts = alerts_by_status.get("pending", 0)
    in_review_alerts = alerts_by_status.get("in_review", 0)
    resolved_alerts = alerts_by_status.get("resolved", 0)
    false_positives = alerts_by_status.get("false_positive", 0)

    # Critical and high severity
    critical_alerts = (
        db.query(func.count(Alert.id))
        .filter(and_(Alert.created_at >= start_date, Alert.severity == "critical"))
        .scalar()
        or 0
    )

    high_severity_alerts = (
        db.query(func.count(Alert.id))
        .filter(and_(Alert.created_at >= start_date, Alert.severity == "high"))
        .scalar()
        or 0
    )

    # Alerts by type
    type_results = (
        db.query(Alert.alert_type, func.count(Alert.id).label("count"))
        .filter(Alert.created_at >= start_date)
        .group_by(Alert.alert_type)
        .all()
    )

    alerts_by_type = {row.alert_type: row.count for row in type_results}

    return AlertStatistics(
        total_alerts=total_alerts,
        pending_alerts=pending_alerts,
        in_review_alerts=in_review_alerts,
        resolved_alerts=resolved_alerts,
        false_positives=false_positives,
        critical_alerts=critical_alerts,
        high_severity_alerts=high_severity_alerts,
        alerts_by_type=alerts_by_type,
        alerts_by_status=alerts_by_status,
        by_status=alerts_by_status,
        by_severity=alerts_by_severity,
    )


def _get_transaction_statistics(db: Session, start_date: datetime) -> TransactionStatistics:
    """Get transaction statistics for dashboard."""
    # Total transactions and volume
    total_result = (
        db.query(
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.amount).label("volume"),
            func.avg(Transaction.amount).label("avg_amount"),
        )
        .filter(Transaction.timestamp >= start_date)
        .first()
    )

    # Transactions by status
    flagged_count = (
        db.query(func.count(Transaction.id))
        .filter(and_(Transaction.timestamp >= start_date, Transaction.status == "flagged"))
        .scalar()
        or 0
    )

    blocked_count = (
        db.query(func.count(Transaction.id))
        .filter(and_(Transaction.timestamp >= start_date, Transaction.status == "blocked"))
        .scalar()
        or 0
    )

    high_risk_count = (
        db.query(func.count(Transaction.id))
        .filter(and_(Transaction.timestamp >= start_date, Transaction.risk_level == "high"))
        .scalar()
        or 0
    )

    # Transactions by country
    country_results = (
        db.query(Transaction.country_code, func.count(Transaction.id).label("count"))
        .filter(and_(Transaction.timestamp >= start_date, Transaction.country_code.isnot(None)))
        .group_by(Transaction.country_code)
        .all()
    )

    transactions_by_country = {row.country_code: row.count for row in country_results}

    # Transactions by type
    type_results = (
        db.query(Transaction.transaction_type, func.count(Transaction.id).label("count"))
        .filter(and_(Transaction.timestamp >= start_date, Transaction.transaction_type.isnot(None)))
        .group_by(Transaction.transaction_type)
        .all()
    )

    transactions_by_type = {row.transaction_type: row.count for row in type_results}

    return TransactionStatistics(
        total_transactions=total_result.count or 0,
        total_volume=total_result.volume or 0,
        flagged_transactions=flagged_count,
        blocked_transactions=blocked_count,
        high_risk_transactions=high_risk_count,
        transactions_by_country=transactions_by_country,
        transactions_by_type=transactions_by_type,
        average_transaction_amount=total_result.avg_amount or 0,
    )


def _get_health_recommendations(stuck_alerts: int, unprocessed_txns: int) -> List[str]:
    """Generate health recommendations based on system status."""
    recommendations = []

    if stuck_alerts > 100:
        recommendations.append(
            "CRITICAL: More than 100 alerts stuck in pending status. Increase analyst capacity or review alert triage process."
        )
    elif stuck_alerts > 50:
        recommendations.append(
            "WARNING: High number of pending alerts. Consider reviewing alert prioritization."
        )
    elif stuck_alerts > 0:
        recommendations.append(
            f"{stuck_alerts} alerts pending for >24 hours. Review and assign to analysts."
        )

    if unprocessed_txns > 1000:
        recommendations.append(
            "CRITICAL: Large transaction processing backlog. Check background worker status."
        )
    elif unprocessed_txns > 100:
        recommendations.append(
            "WARNING: Transaction processing delay detected. Monitor worker performance."
        )

    if not recommendations:
        recommendations.append("All systems operating normally. No action required.")

    return recommendations

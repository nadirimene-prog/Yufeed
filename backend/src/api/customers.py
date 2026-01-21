"""
Customer Investigation API

Provides comprehensive customer investigation endpoints including:
- Customer profiles with risk assessment
- Investigation timeline
- Transaction analytics
- Network analysis preview
- Regulatory context
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.database import get_db
from src.models.transaction_models import (
    Transaction, Alert, Case, UserRiskProfile, MonitoringRule
)

router = APIRouter(prefix="/api/customers", tags=["customers"])


# ============================================================================
# CUSTOMER INVESTIGATION
# ============================================================================

@router.get("/{customer_id}/investigation")
def get_customer_investigation(
    customer_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive investigation data for a customer.

    Returns:
        - profile: Customer risk profile and KYC status
        - timeline: Chronological events (risk changes, alerts, cases)
        - alerts: Customer's alerts summary
        - transactions: Transaction summary
        - network_preview: Related users and connections
        - regulatory_context: Applicable regulations
    """
    # Get risk profile
    risk_profile = db.query(UserRiskProfile).filter(
        UserRiskProfile.user_id == customer_id
    ).first()

    if not risk_profile:
        # Create minimal profile if doesn't exist
        profile = {
            "user_id": customer_id,
            "risk_level": "unknown",
            "risk_score": 0,
            "kyc_status": "unknown",
            "total_alerts": 0,
            "critical_alerts": 0
        }
    else:
        profile = {
            "user_id": risk_profile.user_id,
            "risk_level": risk_profile.risk_level,
            "risk_score": risk_profile.overall_risk_score,
            "risk_factors": risk_profile.risk_factors,
            "kyc_status": risk_profile.kyc_status,
            "enhanced_due_diligence": risk_profile.enhanced_due_diligence,
            "sanctions_match": risk_profile.sanctions_match,
            "sanctions_details": risk_profile.sanctions_details,
            "primary_country": risk_profile.primary_country,
            "high_risk_jurisdictions": risk_profile.high_risk_jurisdictions,
            "total_alerts": risk_profile.total_alerts,
            "critical_alerts": risk_profile.critical_alerts,
            "transaction_velocity_30d": risk_profile.transaction_velocity_30d,
            "total_transaction_amount_30d": float(risk_profile.total_transaction_amount_30d) if risk_profile.total_transaction_amount_30d else 0,
            "last_risk_update": risk_profile.last_risk_update.isoformat() if risk_profile.last_risk_update else None
        }

    # Get timeline events
    timeline = _build_customer_timeline(customer_id, db)

    # Get alerts summary
    alerts = _get_customer_alerts_summary(customer_id, db)

    # Get transactions summary
    transactions = _get_customer_transactions_summary(customer_id, db)

    # Get network preview
    network_preview = _get_network_preview(customer_id, db)

    # Get regulatory context
    regulatory_context = _get_regulatory_context(customer_id, db)

    return {
        "customer_id": customer_id,
        "timestamp": datetime.utcnow().isoformat(),
        "profile": profile,
        "timeline": timeline,
        "alerts": alerts,
        "transactions": transactions,
        "network_preview": network_preview,
        "regulatory_context": regulatory_context
    }


def _build_customer_timeline(customer_id: str, db: Session, limit: int = 50) -> List[Dict]:
    """Build chronological timeline of customer events."""
    events = []

    # Get alerts
    alerts = db.query(Alert).filter(
        Alert.user_id == customer_id
    ).order_by(desc(Alert.created_at)).limit(20).all()

    for alert in alerts:
        events.append({
            "id": f"alert_{alert.id}",
            "type": "alert",
            "timestamp": alert.created_at.isoformat() if alert.created_at else None,
            "title": f"Alert: {alert.alert_type}",
            "description": alert.description or f"{alert.severity} severity alert",
            "severity": alert.severity,
            "status": alert.status,
            "metadata": {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type,
                "sar_filed": alert.sar_filed
            }
        })

    # Get cases
    cases = db.query(Case).filter(
        Case.related_users.contains([customer_id])
    ).order_by(desc(Case.created_at)).limit(10).all()

    for case in cases:
        events.append({
            "id": f"case_{case.id}",
            "type": "case",
            "timestamp": case.created_at.isoformat() if case.created_at else None,
            "title": f"Case: {case.title}",
            "description": case.description or f"{case.case_type} case opened",
            "severity": "high" if case.priority <= 2 else "medium",
            "status": case.status,
            "metadata": {
                "case_id": case.case_id,
                "case_type": case.case_type,
                "outcome": case.outcome
            }
        })

    # Get significant transactions (high risk)
    high_risk_txs = db.query(Transaction).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.risk_level.in_(['high', 'critical'])
        )
    ).order_by(desc(Transaction.created_at)).limit(10).all()

    for tx in high_risk_txs:
        events.append({
            "id": f"tx_{tx.id}",
            "type": "transaction",
            "timestamp": tx.created_at.isoformat() if tx.created_at else None,
            "title": f"High Risk Transaction",
            "description": f"{tx.transaction_type}: {tx.amount} {tx.currency}",
            "severity": tx.risk_level,
            "status": tx.status,
            "metadata": {
                "transaction_id": tx.transaction_id,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "risk_score": tx.risk_score
            }
        })

    # Sort by timestamp descending
    events.sort(key=lambda x: x['timestamp'] or '', reverse=True)

    return events[:limit]


def _get_customer_alerts_summary(customer_id: str, db: Session) -> Dict:
    """Get customer's alerts summary."""
    alerts = db.query(Alert).filter(Alert.user_id == customer_id)

    total = alerts.count()
    pending = alerts.filter(Alert.status == 'pending').count()
    in_review = alerts.filter(Alert.status == 'in_review').count()
    escalated = alerts.filter(Alert.status == 'escalated').count()
    resolved = alerts.filter(Alert.status == 'resolved').count()
    false_positives = alerts.filter(Alert.status == 'false_positive').count()

    # By severity
    critical = alerts.filter(Alert.severity == 'critical').count()
    high = alerts.filter(Alert.severity == 'high').count()

    # By type
    type_counts = db.query(
        Alert.alert_type,
        func.count(Alert.id)
    ).filter(
        Alert.user_id == customer_id
    ).group_by(Alert.alert_type).all()

    # Recent alerts
    recent = alerts.order_by(desc(Alert.created_at)).limit(5).all()

    return {
        "total": total,
        "pending": pending,
        "in_review": in_review,
        "escalated": escalated,
        "resolved": resolved,
        "false_positives": false_positives,
        "critical": critical,
        "high": high,
        "by_type": {row[0]: row[1] for row in type_counts},
        "recent": [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in recent
        ]
    }


def _get_customer_transactions_summary(customer_id: str, db: Session) -> Dict:
    """Get customer's transaction summary."""
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # All time stats
    all_txs = db.query(Transaction).filter(Transaction.user_id == customer_id)
    total_count = all_txs.count()

    # 30 day stats
    recent_txs = all_txs.filter(Transaction.created_at >= thirty_days_ago)
    recent_count = recent_txs.count()

    total_amount = db.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= thirty_days_ago
        )
    ).scalar() or 0

    avg_amount = db.query(func.avg(Transaction.amount)).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= thirty_days_ago
        )
    ).scalar() or 0

    # Risk distribution
    risk_dist = db.query(
        Transaction.risk_level,
        func.count(Transaction.id)
    ).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= thirty_days_ago
        )
    ).group_by(Transaction.risk_level).all()

    # Country distribution
    country_dist = db.query(
        Transaction.country_code,
        func.count(Transaction.id),
        func.sum(Transaction.amount)
    ).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= thirty_days_ago,
            Transaction.country_code.isnot(None)
        )
    ).group_by(Transaction.country_code).all()

    return {
        "total_count": total_count,
        "recent_count": recent_count,
        "total_amount_30d": float(total_amount),
        "avg_amount_30d": round(float(avg_amount), 2),
        "risk_distribution": {row[0]: row[1] for row in risk_dist if row[0]},
        "country_distribution": [
            {
                "country_code": row[0],
                "count": row[1],
                "total_amount": float(row[2]) if row[2] else 0
            }
            for row in country_dist
        ]
    }


def _get_network_preview(customer_id: str, db: Session) -> Dict:
    """Get preview of customer's network connections."""
    # Find related users through transactions
    # Users who received money from this customer
    recipients = db.query(Transaction.recipient_id).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.recipient_id.isnot(None),
            Transaction.recipient_id != customer_id
        )
    ).distinct().limit(20).all()

    # Users who sent money to this customer
    senders = db.query(Transaction.user_id).filter(
        and_(
            Transaction.recipient_id == customer_id,
            Transaction.user_id != customer_id
        )
    ).distinct().limit(20).all()

    recipient_ids = set(r[0] for r in recipients if r[0])
    sender_ids = set(s[0] for s in senders if s[0])

    # Combined unique connections
    connected_users = recipient_ids | sender_ids

    # Check for shared attributes (simplified)
    # In production, this would check IP addresses, device fingerprints, etc.

    return {
        "connected_users": len(connected_users),
        "recipients": len(recipient_ids),
        "senders": len(sender_ids),
        "suspicious_clusters": 0,  # Would be calculated by network analysis
        "shared_attributes": {
            "ip_addresses": 0,
            "devices": 0,
            "accounts": 0
        },
        "preview_connections": list(connected_users)[:10]
    }


def _get_regulatory_context(customer_id: str, db: Session) -> Dict:
    """Get regulatory context for the customer."""
    # Get alerts with regulatory context
    alerts_with_regs = db.query(Alert).filter(
        and_(
            Alert.user_id == customer_id,
            Alert.regulation_context.isnot(None)
        )
    ).limit(10).all()

    regulations = []
    seen_regs = set()

    for alert in alerts_with_regs:
        if alert.related_regulations:
            for reg in alert.related_regulations:
                if reg not in seen_regs:
                    seen_regs.add(reg)
                    regulations.append({
                        "regulation_id": reg,
                        "source_alert": alert.alert_id
                    })

    # Get risk profile for EDD status
    risk_profile = db.query(UserRiskProfile).filter(
        UserRiskProfile.user_id == customer_id
    ).first()

    edd_required = False
    edd_reasons = []

    if risk_profile:
        if risk_profile.risk_level in ['high', 'critical']:
            edd_required = True
            edd_reasons.append("High risk score")
        if risk_profile.sanctions_match:
            edd_required = True
            edd_reasons.append("Potential sanctions match")
        if risk_profile.high_risk_jurisdictions:
            edd_required = True
            edd_reasons.append("High-risk jurisdiction exposure")

    return {
        "applicable_regulations": regulations,
        "enhanced_due_diligence_required": edd_required,
        "edd_reasons": edd_reasons,
        "compliance_notes": [
            "AMLD6 Art. 18: Enhanced due diligence measures" if edd_required else None,
            "EU Reg 2015/847: Funds transfer information" if regulations else None
        ]
    }


# ============================================================================
# CUSTOMER ANALYTICS
# ============================================================================

@router.get("/{customer_id}/analytics")
def get_customer_analytics(
    customer_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get transaction analytics for embedded charts.

    Returns:
        - volume_by_day: Transaction counts by day
        - amount_by_day: Transaction amounts by day
        - amount_buckets: Distribution of transaction amounts
        - type_distribution: Transactions by type
        - risk_trend: Risk score trend over time
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Volume by day
    volume_by_day = db.query(
        func.date_trunc('day', Transaction.created_at).label('date'),
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        )
    ).group_by('date').order_by('date').all()

    # Amount buckets
    amount_buckets = _calculate_amount_buckets(customer_id, start_date, end_date, db)

    # Type distribution
    type_dist = db.query(
        Transaction.transaction_type,
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= start_date
        )
    ).group_by(Transaction.transaction_type).all()

    # Risk trend (average risk score by week)
    risk_trend = db.query(
        func.date_trunc('week', Transaction.created_at).label('week'),
        func.avg(Transaction.risk_score).label('avg_risk')
    ).filter(
        and_(
            Transaction.user_id == customer_id,
            Transaction.created_at >= start_date
        )
    ).group_by('week').order_by('week').all()

    return {
        "customer_id": customer_id,
        "period_days": days,
        "volume_by_day": [
            {
                "date": row.date.isoformat() if row.date else None,
                "count": row.count,
                "total": float(row.total) if row.total else 0
            }
            for row in volume_by_day
        ],
        "amount_buckets": amount_buckets,
        "type_distribution": [
            {
                "type": row.transaction_type,
                "count": row.count,
                "total": float(row.total) if row.total else 0
            }
            for row in type_dist
        ],
        "risk_trend": [
            {
                "week": row.week.isoformat() if row.week else None,
                "avg_risk": round(float(row.avg_risk), 1) if row.avg_risk else 0
            }
            for row in risk_trend
        ]
    }


def _calculate_amount_buckets(
    customer_id: str,
    start_date: datetime,
    end_date: datetime,
    db: Session
) -> List[Dict]:
    """Calculate transaction amount distribution in buckets."""
    buckets = [
        (0, 100, "€0-100"),
        (100, 1000, "€100-1k"),
        (1000, 5000, "€1k-5k"),
        (5000, 10000, "€5k-10k"),
        (10000, 50000, "€10k-50k"),
        (50000, float('inf'), "€50k+")
    ]

    result = []
    for min_amt, max_amt, label in buckets:
        query = db.query(func.count(Transaction.id)).filter(
            and_(
                Transaction.user_id == customer_id,
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date,
                Transaction.amount >= min_amt
            )
        )
        if max_amt != float('inf'):
            query = query.filter(Transaction.amount < max_amt)

        count = query.scalar() or 0
        result.append({"range": label, "count": count})

    return result


# ============================================================================
# CUSTOMER LIST
# ============================================================================

@router.get("/")
def list_customers(
    risk_level: Optional[str] = Query(None, enum=["low", "medium", "high", "critical"]),
    has_alerts: Optional[bool] = None,
    min_risk_score: Optional[int] = Query(None, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List customers with filtering options.
    """
    query = db.query(UserRiskProfile)

    if risk_level:
        query = query.filter(UserRiskProfile.risk_level == risk_level)

    if min_risk_score is not None:
        query = query.filter(UserRiskProfile.overall_risk_score >= min_risk_score)

    if has_alerts is not None:
        if has_alerts:
            query = query.filter(UserRiskProfile.total_alerts > 0)
        else:
            query = query.filter(UserRiskProfile.total_alerts == 0)

    total = query.count()

    customers = query.order_by(
        desc(UserRiskProfile.overall_risk_score)
    ).offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "user_id": c.user_id,
                "risk_level": c.risk_level,
                "risk_score": c.overall_risk_score,
                "total_alerts": c.total_alerts,
                "critical_alerts": c.critical_alerts,
                "kyc_status": c.kyc_status,
                "sanctions_match": c.sanctions_match,
                "last_risk_update": c.last_risk_update.isoformat() if c.last_risk_update else None
            }
            for c in customers
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }

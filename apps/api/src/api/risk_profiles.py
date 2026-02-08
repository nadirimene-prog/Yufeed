"""
User Risk Profiles API
Manages user risk assessments and behavioral analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from src.database import get_db
from src.models.transaction_models import UserRiskProfile, Transaction, Alert
from src.schemas.transaction_schemas import UserRiskProfileResponse
from src.services.risk_scoring import RiskScoringService

router = APIRouter(prefix="/api/risk-profiles", tags=["risk-profiles"])


@router.get("/", response_model=List[UserRiskProfileResponse])
def list_risk_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    risk_level: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    sanctions_match: Optional[bool] = None,
    enhanced_dd: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    List user risk profiles with filtering.
    """
    query = db.query(UserRiskProfile)

    if risk_level:
        query = query.filter(UserRiskProfile.risk_level == risk_level)

    if min_risk_score is not None:
        query = query.filter(UserRiskProfile.overall_risk_score >= min_risk_score)

    if sanctions_match is not None:
        query = query.filter(UserRiskProfile.sanctions_match == sanctions_match)

    if enhanced_dd is not None:
        query = query.filter(UserRiskProfile.enhanced_due_diligence == enhanced_dd)

    # Order by risk score descending
    query = query.order_by(UserRiskProfile.overall_risk_score.desc())

    profiles = query.offset(skip).limit(limit).all()

    return profiles


@router.get("/{user_id}", response_model=UserRiskProfileResponse)
def get_risk_profile(user_id: str, db: Session = Depends(get_db)):
    """
    Get risk profile for a specific user.
    """
    profile = db.query(UserRiskProfile).filter(UserRiskProfile.user_id == user_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Risk profile not found")

    return profile


@router.post("/{user_id}/recalculate", response_model=UserRiskProfileResponse)
def recalculate_risk_profile(user_id: str, db: Session = Depends(get_db)):
    """
    Manually trigger risk profile recalculation for a user.
    """
    risk_service = RiskScoringService(db)

    try:
        profile = risk_service.update_user_risk_profile(user_id)
        return profile

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")


@router.get("/high-risk/list", response_model=List[UserRiskProfileResponse])
def list_high_risk_users(limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    """
    Get list of high-risk users (high or critical risk level).
    """
    profiles = (
        db.query(UserRiskProfile)
        .filter(UserRiskProfile.risk_level.in_(["high", "critical"]))
        .order_by(UserRiskProfile.overall_risk_score.desc())
        .limit(limit)
        .all()
    )

    return profiles


@router.get("/{user_id}/activity")
def get_user_activity_summary(
    user_id: str, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)
):
    """
    Get activity summary for a user.
    """
    start_date = utc_now() - timedelta(days=days)

    # Get transactions
    transactions = (
        db.query(Transaction)
        .filter(and_(Transaction.user_id == user_id, Transaction.timestamp >= start_date))
        .all()
    )

    # Get alerts
    alerts = db.query(Alert).filter(Alert.user_id == user_id).all()

    # Calculate statistics
    total_volume = sum(tx.amount for tx in transactions)
    avg_amount = total_volume / len(transactions) if transactions else 0

    return {
        "user_id": user_id,
        "period_days": days,
        "transaction_count": len(transactions),
        "total_volume": float(total_volume),
        "average_amount": float(avg_amount),
        "alert_count": len(alerts),
        "critical_alerts": sum(1 for a in alerts if a.severity == "critical"),
        "last_activity": max([tx.timestamp for tx in transactions]) if transactions else None,
    }


@router.get("/statistics/overview")
def get_risk_profile_statistics(db: Session = Depends(get_db)):
    """
    Get risk profile statistics.
    """
    total_profiles = db.query(func.count(UserRiskProfile.id)).scalar() or 0

    # Profiles by risk level
    risk_level_results = (
        db.query(UserRiskProfile.risk_level, func.count(UserRiskProfile.id).label("count"))
        .group_by(UserRiskProfile.risk_level)
        .all()
    )

    profiles_by_risk = {row.risk_level: row.count for row in risk_level_results}

    # Sanctions matches
    sanctions_matches = (
        db.query(func.count(UserRiskProfile.id))
        .filter(UserRiskProfile.sanctions_match == True)
        .scalar()
        or 0
    )

    # Enhanced DD required
    edd_required = (
        db.query(func.count(UserRiskProfile.id))
        .filter(UserRiskProfile.enhanced_due_diligence == True)
        .scalar()
        or 0
    )

    return {
        "total_profiles": total_profiles,
        "profiles_by_risk_level": profiles_by_risk,
        "sanctions_matches": sanctions_matches,
        "enhanced_dd_required": edd_required,
        "high_risk_count": profiles_by_risk.get("high", 0) + profiles_by_risk.get("critical", 0),
    }

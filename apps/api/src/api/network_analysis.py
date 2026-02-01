"""
Network Analysis API
Detect fraud rings and suspicious networks.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from src.database import get_db
from src.services.network_analysis import NetworkAnalyzer

router = APIRouter(prefix="/api/network", tags=["network-analysis"])


@router.get("/analyze/{user_id}")
def analyze_user_network(
    user_id: str,
    depth: int = Query(2, ge=1, le=3),
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Analyze network of connections for a user.

    Detects:
    - Circular transaction flows (money laundering)
    - Shared IP addresses/devices (identity fraud)
    - Suspicious clusters (fraud rings)

    depth: Network depth to analyze (1-3 hops)
    days: Historical period to analyze
    """
    analyzer = NetworkAnalyzer(db)

    try:
        analysis = analyzer.analyze_user_network(user_id, depth, days)
        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Network analysis failed: {str(e)}")


@router.get("/related/{user_id}")
def find_related_users(
    user_id: str,
    relationship_type: str = Query("all", pattern="^(all|transaction|ip|device)$"),
    db: Session = Depends(get_db)
):
    """
    Find users related to a given user.

    relationship_type:
    - all: Any relationship
    - transaction: Connected via transactions
    - ip: Shared IP address
    - device: Shared device fingerprint
    """
    analyzer = NetworkAnalyzer(db)

    try:
        related = analyzer.find_related_users(user_id, relationship_type)

        return {
            "user_id": user_id,
            "relationship_type": relationship_type,
            "related_users": related,
            "count": len(related)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Related users search failed: {str(e)}")


@router.get("/fraud-rings/detect")
def detect_fraud_rings(
    min_cluster_size: int = Query(3, ge=2),
    min_suspicion_score: float = Query(50.0, ge=0, le=100),
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Detect potential fraud rings across all users.

    Scans for suspicious clusters of connected users.
    """
    from src.models.transaction_models import UserRiskProfile

    analyzer = NetworkAnalyzer(db)

    # Get high-risk users to start analysis
    high_risk_users = db.query(UserRiskProfile).filter(
        UserRiskProfile.risk_level.in_(['high', 'critical'])
    ).limit(50).all()

    fraud_rings = []

    for profile in high_risk_users:
        analysis = analyzer.analyze_user_network(profile.user_id, depth=2, days=days)

        # Check for suspicious clusters
        if analysis['risk_indicators']['suspicious_clusters']:
            for cluster in analysis['risk_indicators']['suspicious_clusters']:
                if (cluster['connection_count'] >= min_cluster_size and
                    cluster['suspicion_score'] >= min_suspicion_score):

                    fraud_rings.append({
                        "center_user": profile.user_id,
                        "cluster": cluster,
                        "network_risk_score": analysis['network_risk_score']
                    })

        if len(fraud_rings) >= limit:
            break

    # Sort by suspicion score
    fraud_rings.sort(key=lambda x: x['cluster']['suspicion_score'], reverse=True)

    return {
        "fraud_rings_detected": len(fraud_rings),
        "rings": fraud_rings[:limit],
        "analysis_period_days": days
    }

"""
Cached query functions for hot endpoints.
Phase 4A: Task 3.2 & 3.3 - Implement Caching for Hot Endpoints
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from src.cache.cache_manager import cache_manager, cached, cache_aside
from src.models.transaction_models import Alert, MonitoringRule, Transaction
from src.models.models import LegalDocument

# ============================================================================
# USER RISK PROFILES (5min TTL)
# ============================================================================


def get_cached_user_risk_profile(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user risk profile with 5-minute cache.

    Includes:
    - Risk score
    - Alert count
    - Transaction volume
    - Geographic patterns
    """
    return cache_aside(
        namespace="user_risk_profile",
        key=f"user:{user_id}",
        loader=lambda: _compute_user_risk_profile(db, user_id),
        ttl=300,  # 5 minutes
        cache_type="user_profile",
    )


def _compute_user_risk_profile(db: Session, user_id: str) -> Dict[str, Any]:
    """Compute user risk profile from database."""
    # Get recent transactions
    recent_txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id, Transaction.timestamp >= utc_now() - timedelta(days=30)
        )
        .all()
    )

    # Get alerts
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == user_id, Alert.status.in_(["pending", "in_review"]))
        .all()
    )

    # Calculate metrics
    total_volume = sum(float(txn.amount) for txn in recent_txns)
    avg_transaction = total_volume / len(recent_txns) if recent_txns else 0

    countries = set(txn.country_code for txn in recent_txns if txn.country_code)

    risk_score = 0
    if alerts:
        risk_score = sum(float(alert.risk_score or 0) for alert in alerts) / len(alerts)

    return {
        "user_id": user_id,
        "risk_score": round(risk_score, 2),
        "alert_count": len(alerts),
        "transaction_count_30d": len(recent_txns),
        "total_volume_30d": round(total_volume, 2),
        "avg_transaction_amount": round(avg_transaction, 2),
        "unique_countries": len(countries),
        "countries": list(countries),
        "computed_at": utc_now().isoformat(),
    }


def invalidate_user_risk_profile(user_id: str):
    """Invalidate cached user risk profile."""
    cache_manager.delete("user_risk_profile", f"user:{user_id}")


# ============================================================================
# RULE DEFINITIONS (10min TTL)
# ============================================================================


@cached(namespace="rules", key_prefix="rule", ttl=600, cache_type="rules")
def get_cached_rule(db: Session, rule_id: str) -> Optional[Dict[str, Any]]:
    """
    Get rule definition with 10-minute cache.
    """
    rule = db.query(MonitoringRule).filter(MonitoringRule.rule_id == rule_id).first()

    if not rule:
        return None

    return {
        "rule_id": rule.rule_id,
        "name": rule.name,
        "description": rule.description,
        "category": rule.category,
        "severity": rule.severity,
        "conditions": rule.conditions,
        "thresholds": rule.thresholds,
        "enabled": rule.enabled,
        "version": rule.version,
    }


def get_cached_active_rules(db: Session) -> List[Dict[str, Any]]:
    """
    Get all active rules with 10-minute cache.
    """
    return cache_aside(
        namespace="rules",
        key="all_active",
        loader=lambda: _fetch_active_rules(db),
        ttl=600,
        cache_type="rules",
    )


def _fetch_active_rules(db: Session) -> List[Dict[str, Any]]:
    """Fetch active rules from database."""
    rules = db.query(MonitoringRule).filter(MonitoringRule.enabled == True).all()

    return [
        {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "category": rule.category,
            "severity": rule.severity,
            "conditions": rule.conditions,
            "thresholds": rule.thresholds,
        }
        for rule in rules
    ]


def invalidate_rules_cache():
    """Invalidate all cached rules."""
    cache_manager.clear_namespace("rules")


# ============================================================================
# FEATURE AGGREGATIONS (1min TTL)
# ============================================================================


def get_cached_user_features(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Get computed features for user with 1-minute cache.

    Features include:
    - Transaction velocity (24h, 7d, 30d)
    - Volume aggregations
    - Unique counterparties
    - Country diversity
    """
    return cache_aside(
        namespace="features",
        key=f"user:{user_id}",
        loader=lambda: _compute_user_features(db, user_id),
        ttl=60,  # 1 minute
        cache_type="features",
    )


def _compute_user_features(db: Session, user_id: str) -> Dict[str, Any]:
    """Compute user features from transactions."""
    now = utc_now()

    # Get transactions for different windows
    txns_24h = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.timestamp >= now - timedelta(hours=24))
        .all()
    )

    txns_7d = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.timestamp >= now - timedelta(days=7))
        .all()
    )

    txns_30d = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.timestamp >= now - timedelta(days=30))
        .all()
    )

    return {
        "user_id": user_id,
        # Velocity features
        "transaction_count_24h": len(txns_24h),
        "transaction_count_7d": len(txns_7d),
        "transaction_count_30d": len(txns_30d),
        # Volume features
        "total_volume_24h": sum(float(t.amount) for t in txns_24h),
        "total_volume_7d": sum(float(t.amount) for t in txns_7d),
        "total_volume_30d": sum(float(t.amount) for t in txns_30d),
        # Counterparty features
        "unique_counterparties_24h": len(
            set(t.counterparty_id for t in txns_24h if t.counterparty_id)
        ),
        "unique_counterparties_7d": len(
            set(t.counterparty_id for t in txns_7d if t.counterparty_id)
        ),
        # Geographic features
        "unique_countries_30d": len(set(t.country_code for t in txns_30d if t.country_code)),
        "computed_at": utc_now().isoformat(),
    }


# ============================================================================
# SANCTIONS LISTS (1hour TTL)
# ============================================================================


def get_cached_sanctions_list() -> List[str]:
    """
    Get sanctions list with 1-hour cache.
    This would typically fetch from external API.
    """
    return cache_aside(
        namespace="sanctions",
        key="ofac_sdn_list",
        loader=lambda: _fetch_sanctions_list(),
        ttl=3600,  # 1 hour
        cache_type="sanctions",
    )


def _fetch_sanctions_list() -> List[str]:
    """
    Fetch sanctions list from external source.
    This is a placeholder - would integrate with actual sanctions API.
    """
    # TODO: Integrate with OFAC SDN API, EU sanctions API, etc.
    return ["sanctioned_entity_1", "sanctioned_entity_2", "sanctioned_person_1"]


# ============================================================================
# NETWORK GRAPH DATA (15min TTL)
# ============================================================================


def get_cached_transaction_network(db: Session, user_id: str, depth: int = 2) -> Dict[str, Any]:
    """
    Get transaction network graph with 15-minute cache.

    Returns network of users connected through transactions.
    """
    return cache_aside(
        namespace="network",
        key=f"user:{user_id}:depth:{depth}",
        loader=lambda: _compute_transaction_network(db, user_id, depth),
        ttl=900,  # 15 minutes
        cache_type="network",
    )


def _compute_transaction_network(db: Session, user_id: str, depth: int) -> Dict[str, Any]:
    """Compute transaction network graph."""
    # Get all transactions involving the user
    transactions = (
        db.query(Transaction)
        .filter((Transaction.user_id == user_id) | (Transaction.counterparty_id == user_id))
        .limit(1000)
        .all()
    )

    # Build network
    nodes = set()
    edges = []

    for txn in transactions:
        if txn.user_id:
            nodes.add(txn.user_id)
        if txn.counterparty_id:
            nodes.add(txn.counterparty_id)

        edges.append(
            {
                "from": txn.user_id,
                "to": txn.counterparty_id,
                "amount": float(txn.amount),
                "timestamp": txn.timestamp.isoformat() if txn.timestamp else None,
            }
        )

    return {
        "center_user": user_id,
        "depth": depth,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": list(nodes),
        "edges": edges[:100],  # Limit for performance
        "computed_at": utc_now().isoformat(),
    }


# ============================================================================
# DASHBOARD STATISTICS (30sec TTL)
# ============================================================================


def get_cached_dashboard_stats(db: Session) -> Dict[str, Any]:
    """
    Get dashboard statistics with 30-second cache.

    High-traffic endpoint that benefits from aggressive caching.
    """
    return cache_aside(
        namespace="dashboard",
        key="stats",
        loader=lambda: _compute_dashboard_stats(db),
        ttl=30,  # 30 seconds
        cache_type="dashboard",
    )


def _compute_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Compute dashboard statistics."""
    now = utc_now()

    # Alert counts
    total_alerts = db.query(Alert).count()
    pending_alerts = db.query(Alert).filter(Alert.status == "pending").count()
    critical_alerts = db.query(Alert).filter(Alert.severity == "critical").count()

    # Transaction counts
    total_transactions = db.query(Transaction).count()
    transactions_24h = (
        db.query(Transaction).filter(Transaction.timestamp >= now - timedelta(hours=24)).count()
    )

    # High-risk users
    high_risk_users = (
        db.query(Alert.user_id)
        .filter(
            Alert.severity.in_(["high", "critical"]), Alert.status.in_(["pending", "in_review"])
        )
        .distinct()
        .count()
    )

    return {
        "total_alerts": total_alerts,
        "pending_alerts": pending_alerts,
        "critical_alerts": critical_alerts,
        "total_transactions": total_transactions,
        "transactions_24h": transactions_24h,
        "high_risk_users": high_risk_users,
        "computed_at": now.isoformat(),
    }


# ============================================================================
# SEARCH RESULTS CACHING
# ============================================================================


def get_cached_search_results(
    query: str, filters: Dict[str, Any], page: int = 1, page_size: int = 20
) -> Optional[Dict[str, Any]]:
    """
    Cache search results with pagination.

    Args:
        query: Search query string
        filters: Search filters
        page: Page number
        page_size: Results per page

    Returns:
        Cached search results or None
    """
    import hashlib

    # Create cache key from query parameters
    cache_key_data = f"{query}:{filters}:{page}:{page_size}"
    cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()

    return cache_manager.get("search", cache_key, "search")


def cache_search_results(
    query: str,
    filters: Dict[str, Any],
    page: int,
    page_size: int,
    results: Dict[str, Any],
    ttl: int = 300,
):
    """
    Cache search results.
    """
    import hashlib

    cache_key_data = f"{query}:{filters}:{page}:{page_size}"
    cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()

    cache_manager.set("search", cache_key, results, ttl, "search")


def invalidate_search_cache():
    """Invalidate all cached search results."""
    cache_manager.clear_namespace("search")

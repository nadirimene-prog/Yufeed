"""
Cached query functions for hot endpoints.
Phase 4A: Task 3.2 & 3.3 - Implement Caching for Hot Endpoints
"""

import hashlib
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, case, func
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


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # Fetch once for 30 days and partition in-memory for smaller windows.
    txns_30d = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.timestamp >= cutoff_30d)
        .all()
    )
    txns_7d = []
    txns_24h = []
    for txn in txns_30d:
        timestamp = _as_utc(txn.timestamp)
        if not timestamp:
            continue
        if timestamp >= cutoff_7d:
            txns_7d.append(txn)
        if timestamp >= cutoff_24h:
            txns_24h.append(txn)

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
    tx_24h_cutoff = now - timedelta(hours=24)

    alert_stats = db.query(
        func.count(Alert.id).label("total_alerts"),
        func.sum(case((Alert.status == "pending", 1), else_=0)).label("pending_alerts"),
        func.sum(case((Alert.severity == "critical", 1), else_=0)).label("critical_alerts"),
        func.count(
            func.distinct(
                case(
                    (
                        and_(
                            Alert.severity.in_(["high", "critical"]),
                            Alert.status.in_(["pending", "in_review"]),
                        ),
                        Alert.user_id,
                    ),
                    else_=None,
                )
            )
        ).label("high_risk_users"),
    ).one()

    transaction_stats = db.query(
        func.count(Transaction.id).label("total_transactions"),
        func.sum(case((Transaction.timestamp >= tx_24h_cutoff, 1), else_=0)).label(
            "transactions_24h"
        ),
    ).one()

    return {
        "total_alerts": int(alert_stats.total_alerts or 0),
        "pending_alerts": int(alert_stats.pending_alerts or 0),
        "critical_alerts": int(alert_stats.critical_alerts or 0),
        "total_transactions": int(transaction_stats.total_transactions or 0),
        "transactions_24h": int(transaction_stats.transactions_24h or 0),
        "high_risk_users": int(alert_stats.high_risk_users or 0),
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
    cache_key = _build_search_cache_key(query, filters, page, page_size)

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
    cache_key = _build_search_cache_key(query, filters, page, page_size)

    cache_manager.set("search", cache_key, results, ttl, "search")


def invalidate_search_cache():
    """Invalidate all cached search results."""
    cache_manager.clear_namespace("search")


def _build_search_cache_key(query: str, filters: Dict[str, Any], page: int, page_size: int) -> str:
    """Build canonical cache keys to avoid non-deterministic dict ordering."""
    payload = {
        "query": query,
        "filters": filters or {},
        "page": page,
        "page_size": page_size,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.blake2b(canonical.encode("utf-8"), digest_size=16).hexdigest()

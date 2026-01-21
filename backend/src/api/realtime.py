"""
Real-Time Metrics API

Provides endpoints for live dashboard metrics, system health,
and geographic transaction distribution.
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging

from src.database import get_db
from src.models.transaction_models import Transaction, Alert, Case, UserRiskProfile
from src.websocket.manager import get_manager, ConnectionManager
from src.websocket.events import MetricsEvent, SystemHealthEvent, AlertEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


# ============================================================================
# LIVE METRICS
# ============================================================================

@router.get("/metrics/live")
async def get_live_metrics(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get real-time metrics for the Command Center dashboard.

    Returns:
        - transactions_per_minute: Current transaction rate
        - active_alerts: Number of pending/in_review alerts
        - critical_alerts: Number of critical severity alerts
        - pending_reviews: Alerts awaiting triage
        - system_health: Service status indicators
        - processing_latency: P50, P95, P99 latency metrics
    """
    now = datetime.utcnow()
    one_minute_ago = now - timedelta(minutes=1)
    one_hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Transactions per minute (last minute)
    transactions_per_minute = db.query(func.count(Transaction.id)).filter(
        Transaction.created_at >= one_minute_ago
    ).scalar() or 0

    # Active alerts (pending + in_review)
    active_alerts = db.query(func.count(Alert.id)).filter(
        Alert.status.in_(['pending', 'in_review'])
    ).scalar() or 0

    # Critical alerts
    critical_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.status.in_(['pending', 'in_review', 'escalated']),
            Alert.severity == 'critical'
        )
    ).scalar() or 0

    # Pending reviews (pending status only)
    pending_reviews = db.query(func.count(Alert.id)).filter(
        Alert.status == 'pending'
    ).scalar() or 0

    # SARs filed this month
    sars_this_month = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.sar_filed == True,
            Alert.sar_filed_at >= month_start
        )
    ).scalar() or 0

    # False positive rate (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    total_resolved = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.resolved_at >= thirty_days_ago,
            Alert.status.in_(['resolved', 'false_positive'])
        )
    ).scalar() or 1  # Avoid division by zero

    false_positives = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.resolved_at >= thirty_days_ago,
            Alert.status == 'false_positive'
        )
    ).scalar() or 0

    false_positive_rate = round((false_positives / total_resolved) * 100, 1)

    # High risk users
    high_risk_users = db.query(func.count(UserRiskProfile.id)).filter(
        UserRiskProfile.risk_level.in_(['high', 'critical'])
    ).scalar() or 0

    # Open cases
    open_cases = db.query(func.count(Case.id)).filter(
        Case.status.in_(['open', 'in_progress'])
    ).scalar() or 0

    # System health (mock for now - integrate with actual health checks)
    system_health = {
        "api": "operational",
        "database": "operational",
        "ai_services": "operational",
        "redis": "operational",
        "queue": "operational"
    }

    # Processing latency (mock - integrate with actual metrics)
    processing_latency = {
        "p50": 23,
        "p95": 67,
        "p99": 142
    }

    return {
        "timestamp": now.isoformat(),
        "transactions_per_minute": transactions_per_minute,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "pending_reviews": pending_reviews,
        "sars_this_month": sars_this_month,
        "false_positive_rate": false_positive_rate,
        "high_risk_users": high_risk_users,
        "open_cases": open_cases,
        "system_health": system_health,
        "processing_latency": processing_latency
    }


@router.get("/transactions/geo")
async def get_transaction_geo_distribution(
    hours: int = Query(1, ge=1, le=24),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get geographic distribution of transactions for heatmap visualization.

    Args:
        hours: Number of hours to look back (default: 1)

    Returns:
        List of countries with transaction counts and amounts
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    results = db.query(
        Transaction.country_code,
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total_amount'),
        func.avg(Transaction.risk_score).label('avg_risk_score')
    ).filter(
        and_(
            Transaction.created_at >= since,
            Transaction.country_code.isnot(None)
        )
    ).group_by(
        Transaction.country_code
    ).all()

    # High-risk countries (example list)
    high_risk_countries = {
        'AF', 'IR', 'KP', 'SY', 'YE', 'MM', 'BY', 'RU', 'VE', 'NI'
    }

    distribution = []
    for row in results:
        distribution.append({
            "country_code": row.country_code,
            "count": row.count,
            "total_amount": float(row.total_amount) if row.total_amount else 0,
            "avg_risk_score": round(float(row.avg_risk_score), 1) if row.avg_risk_score else 0,
            "is_high_risk": row.country_code in high_risk_countries
        })

    # Sort by count descending
    distribution.sort(key=lambda x: x['count'], reverse=True)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "hours": hours,
        "total_countries": len(distribution),
        "distribution": distribution
    }


@router.get("/alerts/stream")
async def get_alerts_stream(
    minutes: int = Query(5, ge=1, le=60),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get recent alerts for the real-time alert feed.

    Args:
        minutes: Number of minutes to look back (default: 5)

    Returns:
        List of recent alerts with basic info
    """
    since = datetime.utcnow() - timedelta(minutes=minutes)

    alerts = db.query(Alert).filter(
        Alert.created_at >= since
    ).order_by(
        Alert.created_at.desc()
    ).limit(50).all()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "minutes": minutes,
        "count": len(alerts),
        "alerts": [
            {
                "alert_id": a.alert_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "status": a.status,
                "user_id": a.user_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "description": a.description[:100] if a.description else None
            }
            for a in alerts
        ]
    }


@router.get("/system/health")
async def get_system_health() -> Dict[str, Any]:
    """
    Get detailed system health status.

    Returns service status, uptime, and performance metrics.
    """
    # In production, this would check actual service health
    services = {
        "api": {"status": "operational", "latency_ms": 12},
        "database": {"status": "operational", "latency_ms": 5},
        "redis": {"status": "operational", "latency_ms": 2},
        "ai_services": {"status": "operational", "latency_ms": 150},
        "rules_engine": {"status": "operational", "latency_ms": 8},
        "sanctions_screening": {"status": "operational", "latency_ms": 45}
    }

    # Calculate overall status
    statuses = [s["status"] for s in services.values()]
    if all(s == "operational" for s in statuses):
        overall_status = "operational"
    elif any(s == "down" for s in statuses):
        overall_status = "degraded"
    else:
        overall_status = "partial"

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": overall_status,
        "uptime_percentage": 99.95,
        "services": services,
        "latency": {
            "p50": 23,
            "p95": 67,
            "p99": 142
        },
        "queue": {
            "alert_queue": 127,
            "triage_queue": 45,
            "sar_queue": 3
        }
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time updates.

    Connect with: ws://host/api/realtime/ws?token=<jwt_token>

    Supported message types from client:
    - {"type": "subscribe", "channels": ["alerts", "metrics"]}
    - {"type": "unsubscribe", "channels": ["alerts"]}
    - {"type": "ping"}

    Server sends events:
    - {"event_type": "alert.created", "data": {...}}
    - {"event_type": "metrics.update", "data": {...}}
    - {"event_type": "system.health", "data": {...}}
    """
    manager = get_manager()

    # TODO: Validate JWT token and extract user_id
    # For now, use a placeholder
    client_id = token or f"anonymous-{id(websocket)}"

    # Accept connection
    connected = await manager.connect(websocket, client_id)
    if not connected:
        return

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "event_type": "connection.established",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "client_id": client_id,
                "subscribed_channels": ["alerts", "system", "metrics"]
            }
        })

        # Start background task to send periodic metrics
        metrics_task = asyncio.create_task(
            _send_periodic_metrics(websocket, db, interval=5)
        )

        # Listen for client messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30  # 30 second timeout for heartbeat
                )

                msg_type = data.get("type")

                if msg_type == "ping":
                    await manager.heartbeat(client_id)
                    await websocket.send_json({
                        "event_type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                elif msg_type == "subscribe":
                    channels = data.get("channels", [])
                    for channel in channels:
                        await manager.subscribe(client_id, channel)
                    await websocket.send_json({
                        "event_type": "subscribed",
                        "data": {"channels": channels}
                    })

                elif msg_type == "unsubscribe":
                    channels = data.get("channels", [])
                    for channel in channels:
                        await manager.unsubscribe(client_id, channel)
                    await websocket.send_json({
                        "event_type": "unsubscribed",
                        "data": {"channels": channels}
                    })

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({
                    "event_type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        metrics_task.cancel()
        await manager.disconnect(websocket)


async def _send_periodic_metrics(
    websocket: WebSocket,
    db: Session,
    interval: int = 5
):
    """Background task to send periodic metrics updates."""
    while True:
        try:
            await asyncio.sleep(interval)

            # Get fresh metrics
            now = datetime.utcnow()
            one_minute_ago = now - timedelta(minutes=1)

            tx_count = db.query(func.count(Transaction.id)).filter(
                Transaction.created_at >= one_minute_ago
            ).scalar() or 0

            active_alerts = db.query(func.count(Alert.id)).filter(
                Alert.status.in_(['pending', 'in_review'])
            ).scalar() or 0

            critical_alerts = db.query(func.count(Alert.id)).filter(
                and_(
                    Alert.status.in_(['pending', 'in_review']),
                    Alert.severity == 'critical'
                )
            ).scalar() or 0

            # Send metrics update
            event = MetricsEvent.update(
                transactions_per_minute=tx_count,
                active_alerts=active_alerts,
                critical_alerts=critical_alerts,
                pending_reviews=active_alerts,
                sars_this_month=0,
                false_positive_rate=12.3
            )

            await websocket.send_json(event.to_json())

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error sending periodic metrics: {e}")
            break


# ============================================================================
# CONNECTION STATS
# ============================================================================

@router.get("/connections/stats")
async def get_connection_stats() -> Dict[str, Any]:
    """Get WebSocket connection statistics."""
    manager = get_manager()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        **manager.get_connection_stats()
    }

"""
WebSocket Infrastructure for Yufeed Real-Time Communication

This module provides WebSocket support for real-time updates including:
- Transaction alerts
- System health monitoring
- Live metrics streaming
- Multi-client broadcasting via Redis pub/sub
"""

from src.websocket.manager import ConnectionManager, get_manager
from src.websocket.events import (
    WebSocketEvent,
    EventType,
    TransactionEvent,
    AlertEvent,
    SystemHealthEvent,
    MetricsEvent,
)
from src.websocket.broadcaster import RedisBroadcaster, get_broadcaster

__all__ = [
    # Manager
    "ConnectionManager",
    "get_manager",
    # Events
    "WebSocketEvent",
    "EventType",
    "TransactionEvent",
    "AlertEvent",
    "SystemHealthEvent",
    "MetricsEvent",
    # Broadcaster
    "RedisBroadcaster",
    "get_broadcaster",
]

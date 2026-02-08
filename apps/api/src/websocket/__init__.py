"""
WebSocket module for real-time notifications.
Phase 4B: Task 6 - Real-Time WebSocket Notifications
"""

from src.websocket.manager import ConnectionManager, ws_manager
from src.websocket.events import EventType, NotificationEvent

__all__ = ["ConnectionManager", "ws_manager", "EventType", "NotificationEvent"]

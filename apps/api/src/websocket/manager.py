"""
WebSocket connection manager for real-time notifications.
Phase 4B: Task 6.1 & 6.2 - WebSocket Server Setup & Event Notification System
"""
import logging
import asyncio
import json
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from src.websocket.events import NotificationEvent, EventType
from src.monitoring.metrics import websocket_connections_active, websocket_messages_sent_total

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manage WebSocket connections for real-time notifications.

    Features:
    - Per-user connection management
    - Broadcasting to all connections
    - Targeted user notifications
    - Connection health monitoring
    - Automatic cleanup on disconnect
    """

    def __init__(self):
        # Map of user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # Map of WebSocket -> user_id for reverse lookup
        self.connection_users: Dict[WebSocket, str] = {}

        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        metadata: Optional[Dict] = None
    ):
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID for this connection
            metadata: Optional connection metadata
        """
        await websocket.accept()

        # Register connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id

        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "metadata": metadata or {}
        }

        # Update metrics
        websocket_connections_active.set(self.get_total_connections())

        logger.info(f"WebSocket connected: user={user_id}, total={self.get_total_connections()}")

        # Send welcome message
        await self.send_personal_message(
            websocket,
            {
                "type": "connection.established",
                "message": "Connected to YuFeed real-time notifications",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def disconnect(self, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        user_id = self.connection_users.get(websocket)

        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Remove user entry if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Cleanup
        self.connection_users.pop(websocket, None)
        self.connection_metadata.pop(websocket, None)

        # Update metrics
        websocket_connections_active.set(self.get_total_connections())

        logger.info(f"WebSocket disconnected: user={user_id}, total={self.get_total_connections()}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """
        Send message to a specific WebSocket connection.

        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send message to websocket: {e}")
            self.disconnect(websocket)

    async def send_to_user(self, user_id: str, message: dict):
        """
        Send message to all connections for a specific user.

        Args:
            user_id: Target user ID
            message: Message to send
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return

        connections = self.active_connections[user_id].copy()
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                websocket_messages_sent_total.labels(
                    event_type=message.get("event_type", "unknown")
                ).inc()
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.append(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """
        Broadcast message to all connected users.

        Args:
            message: Message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
        """
        total_sent = 0
        disconnected = []

        for user_id, connections in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue

            for websocket in connections.copy():
                try:
                    await websocket.send_json(message)
                    total_sent += 1
                    websocket_messages_sent_total.labels(
                        event_type=message.get("event_type", "broadcast")
                    ).inc()
                except Exception as e:
                    logger.warning(f"Failed to broadcast to {user_id}: {e}")
                    disconnected.append(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            self.disconnect(ws)

        logger.debug(f"Broadcast sent to {total_sent} connections")

    async def send_notification(
        self,
        notification: NotificationEvent,
        target_user: Optional[str] = None
    ):
        """
        Send notification event to target user or all users.

        Args:
            notification: Notification event to send
            target_user: Optional user ID to send to (broadcasts if None)
        """
        message = {
            "type": "notification",
            "event_type": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "data": notification.data,
            "timestamp": notification.timestamp.isoformat(),
            "priority": notification.priority,
            "link": notification.link
        }

        if target_user:
            await self.send_to_user(target_user, message)
        else:
            await self.broadcast(message)

    async def send_system_alert(
        self,
        message: str,
        severity: str = "info",
        data: Optional[Dict] = None
    ):
        """
        Send system-wide alert to all users.

        Args:
            message: Alert message
            severity: Alert severity (info, warning, error)
            data: Additional data
        """
        alert = {
            "type": "system.alert",
            "event_type": EventType.SYSTEM_ALERT,
            "message": message,
            "severity": severity,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.broadcast(alert)

    async def ping_all(self):
        """
        Send ping to all connections to check health.
        """
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }

        disconnected = []

        for user_id, connections in self.active_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.send_json(ping_message)
                except Exception:
                    disconnected.append(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            self.disconnect(ws)

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def get_user_connections(self, user_id: str) -> int:
        """Get number of connections for a specific user."""
        return len(self.active_connections.get(user_id, set()))

    def get_all_users(self) -> List[str]:
        """Get list of all connected user IDs."""
        return list(self.active_connections.keys())

    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            "total_connections": self.get_total_connections(),
            "total_users": len(self.active_connections),
            "users": {
                user_id: len(connections)
                for user_id, connections in self.active_connections.items()
            }
        }


# Global connection manager instance
ws_manager = ConnectionManager()


# Background task to ping connections
async def websocket_heartbeat_task():
    """
    Background task to send periodic pings to all connections.
    Helps detect and clean up dead connections.
    """
    while True:
        try:
            await asyncio.sleep(30)  # Ping every 30 seconds
            await ws_manager.ping_all()
            logger.debug(f"Heartbeat sent to {ws_manager.get_total_connections()} connections")
        except Exception as e:
            logger.error(f"Heartbeat task error: {e}", exc_info=True)

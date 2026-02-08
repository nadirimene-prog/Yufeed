"""
WebSocket connection manager for real-time notifications.
Phase 4B: Task 6.1 & 6.2 - WebSocket Server Setup & Event Notification System
"""

import logging
import asyncio
from typing import Dict, Set, List, Optional, Tuple
from fastapi import WebSocket
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


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
        # Map of (tenant_id, user_id) -> Set of WebSocket connections
        self.active_connections: Dict[Tuple[str, str], Set[WebSocket]] = {}

        # Map of WebSocket -> (tenant_id, user_id) for reverse lookup
        self.connection_users: Dict[WebSocket, Tuple[str, str]] = {}

        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(
        self, websocket: WebSocket, tenant_id: str, user_id: str, metadata: Optional[Dict] = None
    ):
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            tenant_id: Tenant identifier for this connection
            user_id: User ID for this connection
            metadata: Optional connection metadata
        """
        await websocket.accept()

        # Register connection
        if not tenant_id or not user_id:
            await websocket.close(code=1008)
            return

        key = (tenant_id, user_id)
        if key not in self.active_connections:
            self.active_connections[key] = set()

        self.active_connections[key].add(websocket)
        self.connection_users[websocket] = key

        # Store metadata
        self.connection_metadata[websocket] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "connected_at": utc_now(),
            "metadata": metadata or {},
        }

        # Update metrics
        websocket_connections_active.set(self.get_total_connections())

        logger.info(
            "WebSocket connected: tenant=%s user=%s total=%s",
            tenant_id,
            user_id,
            self.get_total_connections(),
        )

        # Send welcome message
        await self.send_personal_message(
            websocket,
            {
                "type": "connection.established",
                "message": "Connected to YuFeed real-time notifications",
                "tenant_id": tenant_id,
                "user_id": user_id,
                "timestamp": utc_now().isoformat(),
            },
        )

    def disconnect(self, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        key = self.connection_users.get(websocket)

        if key and key in self.active_connections:
            self.active_connections[key].discard(websocket)

            # Remove entry if no more connections
            if not self.active_connections[key]:
                del self.active_connections[key]

        # Cleanup
        self.connection_users.pop(websocket, None)
        self.connection_metadata.pop(websocket, None)

        # Update metrics
        websocket_connections_active.set(self.get_total_connections())

        tenant_id, user_id = key if key else (None, None)
        logger.info(
            "WebSocket disconnected: tenant=%s user=%s total=%s",
            tenant_id,
            user_id,
            self.get_total_connections(),
        )

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

    async def send_to_tenant_user(self, tenant_id: str, user_id: str, message: dict):
        """
        Send message to all connections for a specific tenant user.

        Args:
            tenant_id: Tenant identifier
            user_id: Target user ID
            message: Message to send
        """
        key = (tenant_id, user_id)
        if key not in self.active_connections:
            logger.debug("No active connections for tenant=%s user=%s", tenant_id, user_id)
            return

        connections = self.active_connections[key].copy()
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                websocket_messages_sent_total.labels(
                    event_type=message.get("event_type", "unknown")
                ).inc()
            except Exception as e:
                logger.warning("Failed to send to tenant=%s user=%s: %s", tenant_id, user_id, e)
                disconnected.append(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_to_tenant(self, tenant_id: str, message: dict) -> None:
        """
        Broadcast message to all connected users in a tenant.

        Args:
            tenant_id: Tenant identifier
            message: Message to broadcast
        """
        total_sent = 0
        disconnected = []

        for (tid, user_id), connections in self.active_connections.items():
            if tid != tenant_id:
                continue

            for websocket in connections.copy():
                try:
                    await websocket.send_json(message)
                    total_sent += 1
                    websocket_messages_sent_total.labels(
                        event_type=message.get("event_type", "broadcast")
                    ).inc()
                except Exception as e:
                    logger.warning("Failed to broadcast to tenant=%s user=%s: %s", tid, user_id, e)
                    disconnected.append(websocket)

        # Cleanup disconnected
        for ws in disconnected:
            self.disconnect(ws)

        logger.debug("Tenant broadcast sent: tenant=%s total=%s", tenant_id, total_sent)

    async def broadcast_global(self, message: dict) -> None:
        """Broadcast a message to all connected users (all tenants)."""
        total_sent = 0
        disconnected = []

        for (tenant_id, user_id), connections in self.active_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.send_json(message)
                    total_sent += 1
                    websocket_messages_sent_total.labels(
                        event_type=message.get("event_type", "broadcast")
                    ).inc()
                except Exception as e:
                    logger.warning(
                        "Failed to global broadcast to tenant=%s user=%s: %s", tenant_id, user_id, e
                    )
                    disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws)

        logger.debug("Global broadcast sent to %s connections", total_sent)

    async def broadcast(self, message: dict) -> None:
        """
        Backwards-compatible alias for global broadcasts.

        Prefer `broadcast_to_tenant` for tenant-scoped events and `broadcast_global` for
        intentional cross-tenant (global) messages.
        """
        await self.broadcast_global(message)

    async def send_notification(
        self,
        notification: NotificationEvent,
        tenant_id: Optional[str] = None,
        target_user: Optional[str] = None,
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
            "link": notification.link,
        }

        target = target_user or notification.user_id
        if tenant_id and target:
            await self.send_to_tenant_user(tenant_id, target, message)
        elif tenant_id:
            await self.broadcast_to_tenant(tenant_id, message)
        else:
            await self.broadcast_global(message)

    async def send_system_alert(
        self, message: str, severity: str = "info", data: Optional[Dict] = None
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
            "timestamp": utc_now().isoformat(),
        }

        await self.broadcast_global(alert)

    async def ping_all(self):
        """
        Send ping to all connections to check health.
        """
        ping_message = {"type": "ping", "timestamp": utc_now().isoformat()}

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

    def get_user_connections(self, tenant_id: str, user_id: str) -> int:
        """Get number of connections for a specific tenant user."""
        return len(self.active_connections.get((tenant_id, user_id), set()))

    def get_all_users(self) -> List[str]:
        """Get list of all connected user IDs (may include duplicates across tenants)."""
        return [user_id for (_, user_id) in self.active_connections.keys()]

    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            "total_connections": self.get_total_connections(),
            "total_users": len(self.active_connections),
            "users": {
                f"{tenant_id}:{user_id}": len(connections)
                for (tenant_id, user_id), connections in self.active_connections.items()
            },
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

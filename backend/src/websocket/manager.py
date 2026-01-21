"""
WebSocket Connection Manager

Handles WebSocket connections, authentication, and message routing.
Supports multiple clients per user and channel-based subscriptions.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, List, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from starlette.websockets import WebSocketState

from src.websocket.events import WebSocketEvent, EventType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with support for:
    - Multiple connections per client
    - Channel-based subscriptions
    - Heartbeat mechanism
    - Graceful disconnection
    """

    def __init__(self):
        # client_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # channel -> set of client_ids subscribed
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        # WebSocket -> client_id mapping for reverse lookup
        self.connection_clients: Dict[WebSocket, str] = {}
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        channels: Optional[List[str]] = None
    ) -> bool:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            client_id: Unique identifier for the client (usually user_id)
            channels: Optional list of channels to subscribe to

        Returns:
            True if connection successful, False otherwise
        """
        try:
            await websocket.accept()

            async with self._lock:
                # Add to active connections
                if client_id not in self.active_connections:
                    self.active_connections[client_id] = []
                self.active_connections[client_id].append(websocket)

                # Track reverse mapping
                self.connection_clients[websocket] = client_id

                # Update heartbeat
                self.last_heartbeat[client_id] = datetime.utcnow()

                # Subscribe to channels
                default_channels = ["alerts", "system", "metrics"]
                subscribe_channels = channels or default_channels
                for channel in subscribe_channels:
                    if channel not in self.channel_subscriptions:
                        self.channel_subscriptions[channel] = set()
                    self.channel_subscriptions[channel].add(client_id)

            logger.info(f"Client {client_id} connected. Total connections: {self.connection_count}")
            return True

        except Exception as e:
            logger.error(f"Error connecting client {client_id}: {e}")
            return False

    async def disconnect(self, websocket: WebSocket) -> Optional[str]:
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The disconnected WebSocket

        Returns:
            The client_id of the disconnected client, or None
        """
        async with self._lock:
            client_id = self.connection_clients.get(websocket)
            if not client_id:
                return None

            # Remove from connection tracking
            del self.connection_clients[websocket]

            # Remove from active connections
            if client_id in self.active_connections:
                self.active_connections[client_id] = [
                    ws for ws in self.active_connections[client_id]
                    if ws != websocket
                ]
                # Clean up if no more connections
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]
                    del self.last_heartbeat[client_id]

                    # Remove from all channel subscriptions
                    for channel in self.channel_subscriptions:
                        self.channel_subscriptions[channel].discard(client_id)

            logger.info(f"Client {client_id} disconnected. Total connections: {self.connection_count}")
            return client_id

    async def send_personal(
        self,
        client_id: str,
        event: WebSocketEvent
    ) -> int:
        """
        Send an event to a specific client (all their connections).

        Args:
            client_id: The target client ID
            event: The event to send

        Returns:
            Number of connections the message was sent to
        """
        sent_count = 0
        connections = self.active_connections.get(client_id, [])

        for websocket in connections:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(event.to_json())
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")

        return sent_count

    async def broadcast(
        self,
        event: WebSocketEvent,
        channel: Optional[str] = None,
        exclude_clients: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast an event to all connected clients or a specific channel.

        Args:
            event: The event to broadcast
            channel: Optional channel to broadcast to (None = all clients)
            exclude_clients: Optional set of client_ids to exclude

        Returns:
            Number of clients the message was sent to
        """
        exclude = exclude_clients or set()
        sent_count = 0

        if channel:
            # Send to channel subscribers only
            subscribers = self.channel_subscriptions.get(channel, set())
            target_clients = subscribers - exclude
        else:
            # Send to all clients
            target_clients = set(self.active_connections.keys()) - exclude

        for client_id in target_clients:
            count = await self.send_personal(client_id, event)
            if count > 0:
                sent_count += 1

        return sent_count

    async def broadcast_to_channel(
        self,
        channel: str,
        event: WebSocketEvent
    ) -> int:
        """Convenience method to broadcast to a specific channel."""
        return await self.broadcast(event, channel=channel)

    async def subscribe(self, client_id: str, channel: str):
        """Subscribe a client to a channel."""
        async with self._lock:
            if channel not in self.channel_subscriptions:
                self.channel_subscriptions[channel] = set()
            self.channel_subscriptions[channel].add(client_id)

    async def unsubscribe(self, client_id: str, channel: str):
        """Unsubscribe a client from a channel."""
        async with self._lock:
            if channel in self.channel_subscriptions:
                self.channel_subscriptions[channel].discard(client_id)

    async def heartbeat(self, client_id: str):
        """Update heartbeat timestamp for a client."""
        self.last_heartbeat[client_id] = datetime.utcnow()

    async def check_stale_connections(self, timeout_seconds: int = 60) -> List[str]:
        """
        Find clients that haven't sent a heartbeat recently.

        Args:
            timeout_seconds: Seconds since last heartbeat to consider stale

        Returns:
            List of stale client_ids
        """
        now = datetime.utcnow()
        stale = []
        for client_id, last_beat in self.last_heartbeat.items():
            if (now - last_beat).total_seconds() > timeout_seconds:
                stale.append(client_id)
        return stale

    @property
    def connection_count(self) -> int:
        """Total number of active WebSocket connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    @property
    def client_count(self) -> int:
        """Number of unique connected clients."""
        return len(self.active_connections)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": self.connection_count,
            "unique_clients": self.client_count,
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self.channel_subscriptions.items()
            }
        }


# Global manager instance
_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    """Get or create the global ConnectionManager instance."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager

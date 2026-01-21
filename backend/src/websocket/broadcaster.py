"""
Redis Broadcaster for WebSocket Events

Enables horizontal scaling by using Redis pub/sub to broadcast
events across multiple server instances.
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import redis, use mock if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory broadcaster")


class RedisBroadcaster:
    """
    Redis-based broadcaster for WebSocket events.

    Enables horizontal scaling by publishing events to Redis
    and subscribing to events from other instances.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        channel_prefix: str = "yufeed:ws:"
    ):
        self.redis_url = redis_url
        self.channel_prefix = channel_prefix
        self._redis: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        self._subscriber_task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Callable] = {}
        self._connected = False

    async def connect(self) -> bool:
        """
        Connect to Redis.

        Returns:
            True if connected successfully, False otherwise
        """
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, broadcaster will operate in local mode")
            self._connected = False
            return False

        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()

        self._connected = False
        logger.info("Disconnected from Redis")

    async def publish(
        self,
        channel: str,
        event_type: str,
        data: dict
    ) -> int:
        """
        Publish an event to a channel.

        Args:
            channel: The channel name (e.g., "alerts", "metrics")
            event_type: The event type (e.g., "alert.created")
            data: The event data

        Returns:
            Number of subscribers that received the message
        """
        if not self._connected or not self._redis:
            # Local mode - no Redis
            return 0

        try:
            message = json.dumps({
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            })
            full_channel = f"{self.channel_prefix}{channel}"
            subscribers = await self._redis.publish(full_channel, message)
            logger.debug(f"Published to {full_channel}: {subscribers} subscribers")
            return subscribers
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")
            return 0

    async def subscribe(
        self,
        channel: str,
        handler: Callable[[str, dict], Any]
    ):
        """
        Subscribe to a channel with a handler.

        Args:
            channel: The channel name to subscribe to
            handler: Async function to handle received messages
        """
        full_channel = f"{self.channel_prefix}{channel}"
        self._handlers[full_channel] = handler

        if not self._connected or not self._redis:
            logger.warning(f"Not connected to Redis, handler for {channel} registered but inactive")
            return

        if not self._pubsub:
            self._pubsub = self._redis.pubsub()

        await self._pubsub.subscribe(full_channel)
        logger.info(f"Subscribed to {full_channel}")

        # Start subscriber task if not running
        if not self._subscriber_task or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._listen())

    async def _listen(self):
        """Background task to listen for Redis messages."""
        if not self._pubsub:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                        handler = self._handlers.get(channel)
                        if handler:
                            await handler(channel, data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in message from {channel}")
                    except Exception as e:
                        logger.error(f"Error handling message from {channel}: {e}")
        except asyncio.CancelledError:
            logger.info("Subscriber task cancelled")
        except Exception as e:
            logger.error(f"Error in subscriber task: {e}")

    async def publish_alert(
        self,
        alert_id: str,
        alert_type: str,
        severity: str,
        user_id: str,
        **kwargs
    ) -> int:
        """Convenience method to publish an alert event."""
        return await self.publish(
            channel="alerts",
            event_type="alert.created",
            data={
                "alert_id": alert_id,
                "alert_type": alert_type,
                "severity": severity,
                "user_id": user_id,
                **kwargs
            }
        )

    async def publish_metrics(
        self,
        transactions_per_minute: int,
        active_alerts: int,
        critical_alerts: int,
        **kwargs
    ) -> int:
        """Convenience method to publish metrics update."""
        return await self.publish(
            channel="metrics",
            event_type="metrics.update",
            data={
                "transactions_per_minute": transactions_per_minute,
                "active_alerts": active_alerts,
                "critical_alerts": critical_alerts,
                **kwargs
            }
        )

    async def publish_system_health(
        self,
        services: dict,
        uptime_percentage: float,
        **kwargs
    ) -> int:
        """Convenience method to publish system health update."""
        return await self.publish(
            channel="system",
            event_type="system.health",
            data={
                "services": services,
                "uptime_percentage": uptime_percentage,
                **kwargs
            }
        )

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected


# Global broadcaster instance
_broadcaster: Optional[RedisBroadcaster] = None


def get_broadcaster(redis_url: Optional[str] = None) -> RedisBroadcaster:
    """Get or create the global RedisBroadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        url = redis_url or "redis://localhost:6379"
        _broadcaster = RedisBroadcaster(redis_url=url)
    return _broadcaster

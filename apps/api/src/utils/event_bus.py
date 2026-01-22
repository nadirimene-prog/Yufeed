import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional

try:
    from aiokafka import AIOKafkaProducer
except Exception:  # pragma: no cover - optional dependency in dev
    AIOKafkaProducer = None

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self, bootstrap_servers: str | None = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
        self.producer: AIOKafkaProducer | None = None

    async def start(self):
        if AIOKafkaProducer is None:
            raise RuntimeError("aiokafka is not installed. Install aiokafka or disable the event bus.")
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            self.producer = None

    async def publish(self, topic: str, payload: Dict[str, Any]):
        if not self.producer:
            raise RuntimeError("Producer not started. Call start() first.")
        message = json.dumps(payload).encode("utf-8")
        await self.producer.send_and_wait(topic, message)


_EVENT_BUS: Optional[EventBus] = None
_EVENT_BUS_LOCK = asyncio.Lock()


async def _get_event_bus() -> EventBus:
    global _EVENT_BUS
    async with _EVENT_BUS_LOCK:
        if _EVENT_BUS is None:
            _EVENT_BUS = EventBus()
        if _EVENT_BUS.producer is None:
            await _EVENT_BUS.start()
        return _EVENT_BUS


async def publish_event(topic: str, payload: Dict[str, Any]) -> None:
    bus = await _get_event_bus()
    await bus.publish(topic, payload)


def publish_event_safe(topic: str, payload: Dict[str, Any]) -> None:
    enabled = os.getenv("EVENT_BUS_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.run(publish_event(topic, payload))
        except Exception:
            logger.warning("Event bus publish failed (sync)", exc_info=True)
        return

    try:
        loop.create_task(publish_event(topic, payload))
    except Exception:
        logger.warning("Event bus publish failed (async)", exc_info=True)

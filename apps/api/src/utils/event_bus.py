import os
import json
from typing import Dict, Any
from aiokafka import AIOKafkaProducer

class EventBus:
    def __init__(self, bootstrap_servers: str | None = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
        self.producer: AIOKafkaProducer | None = None

    async def start(self):
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

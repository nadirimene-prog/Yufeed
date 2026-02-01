import pytest
import asyncio

import src.utils.event_bus as event_bus


class FakeProducer:
    def __init__(self, bootstrap_servers=None):
        self.bootstrap_servers = bootstrap_servers
        self.started = False
        self.sent = []

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    async def send_and_wait(self, topic, message):
        self.sent.append((topic, message))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_bus_start_stop_publish(monkeypatch):
    monkeypatch.setattr(event_bus, "AIOKafkaProducer", FakeProducer)

    bus = event_bus.EventBus(bootstrap_servers="localhost:1234")
    await bus.start()
    assert bus.producer is not None

    await bus.publish("topic", {"a": 1})
    assert bus.producer.sent

    await bus.stop()
    assert bus.producer is None


@pytest.mark.unit
def test_publish_event_safe_disabled(monkeypatch):
    monkeypatch.setenv("EVENT_BUS_ENABLED", "false")
    event_bus.publish_event_safe("topic", {"a": 1})


@pytest.mark.unit
def test_publish_event_safe_no_loop(monkeypatch):
    called = {}

    async def fake_publish(topic, payload):
        called["ok"] = True

    monkeypatch.setenv("EVENT_BUS_ENABLED", "true")
    monkeypatch.setattr(event_bus, "publish_event", fake_publish)

    event_bus.publish_event_safe("topic", {"a": 1})
    assert called.get("ok") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_safe_running_loop(monkeypatch):
    called = {"count": 0}

    async def fake_publish(topic, payload):
        called["count"] += 1

    monkeypatch.setenv("EVENT_BUS_ENABLED", "true")
    monkeypatch.setattr(event_bus, "publish_event", fake_publish)

    event_bus.publish_event_safe("topic", {"a": 1})
    await asyncio.sleep(0)
    assert called["count"] == 1

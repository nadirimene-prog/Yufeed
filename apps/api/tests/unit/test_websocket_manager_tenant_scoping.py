import pytest

from src.websocket.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed_code = None
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        self.sent.append(message)

    async def close(self, code: int):
        self.closed_code = code


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_to_tenant_does_not_leak_across_tenants():
    manager = ConnectionManager()

    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()

    await manager.connect(ws_a, tenant_id="tenant-a", user_id="user-1")
    await manager.connect(ws_b, tenant_id="tenant-b", user_id="user-1")

    assert ws_a.accepted is True
    assert ws_b.accepted is True

    # Each connection receives a welcome message on connect.
    assert len(ws_a.sent) == 1
    assert len(ws_b.sent) == 1

    message = {"event_type": "test.event", "payload": {"ok": True}}
    await manager.broadcast_to_tenant("tenant-a", message)

    assert len(ws_a.sent) == 2
    assert ws_a.sent[-1] == message

    assert len(ws_b.sent) == 1
    assert message not in ws_b.sent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_to_tenant_user_is_isolated():
    manager = ConnectionManager()

    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()

    await manager.connect(ws_a, tenant_id="tenant-a", user_id="user-1")
    await manager.connect(ws_b, tenant_id="tenant-b", user_id="user-1")

    message = {"event_type": "test.direct", "payload": {"ok": True}}
    await manager.send_to_tenant_user("tenant-a", "user-1", message)

    assert message in ws_a.sent
    assert message not in ws_b.sent

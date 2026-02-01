import pytest
import json
from fastapi import WebSocketDisconnect

from src.api import websocket as ws_api


class DummyWebSocket:
    def __init__(self, messages=None):
        self.messages = list(messages or [])
        self.sent = []
        self.closed_codes = []

    async def close(self, code=1000):
        self.closed_codes.append(code)

    async def receive_text(self):
        if not self.messages:
            raise WebSocketDisconnect()
        return self.messages.pop(0)

    async def send_json(self, payload):
        self.sent.append(payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_rejects_missing_token(monkeypatch):
    ws = DummyWebSocket()
    await ws_api.websocket_endpoint(ws, token=None)
    assert 1008 in ws.closed_codes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_websocket_ping_pong(monkeypatch):
    payload = {"user_id": "user-1", "sub": "user@example.com", "role": "admin"}

    monkeypatch.setattr(ws_api.JWTHandler, "decode_token", lambda token: payload)
    monkeypatch.setattr(ws_api.JWTHandler, "verify_token_type", lambda payload, _: True)

    connected = {"connected": False, "disconnected": False}

    async def fake_connect(websocket, user_id, metadata):
        connected["connected"] = True

    def fake_disconnect(websocket):
        connected["disconnected"] = True

    monkeypatch.setattr(ws_api.ws_manager, "connect", fake_connect)
    monkeypatch.setattr(ws_api.ws_manager, "disconnect", fake_disconnect)

    ws = DummyWebSocket(messages=[json.dumps({"type": "ping"})])
    await ws_api.websocket_endpoint(ws, token="token")

    assert connected["connected"] is True
    assert connected["disconnected"] is True
    assert ws.sent

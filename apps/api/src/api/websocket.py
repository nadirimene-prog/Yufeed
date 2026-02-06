"""
WebSocket API endpoints for real-time notifications.
"""
import json
import logging
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from src.auth.jwt_handler import JWTHandler
from src.websocket import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None)
):
    """
    WebSocket endpoint for real-time notifications.

    Expects a JWT access token as a query parameter (?token=...).
    """
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = JWTHandler.decode_token(token)
        if not JWTHandler.verify_token_type(payload, "access"):
            await websocket.close(code=1008)
            return

        user_id = payload.get("user_id")
        email = payload.get("sub")
        role = payload.get("role", "user")
        tenant_id = payload.get("tenant_id")

        if not user_id or not email or not tenant_id:
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        return
    except Exception as exc:
        logger.warning(f"WebSocket token validation error: {exc}")
        await websocket.close(code=1011)
        return

    await ws_manager.connect(
        websocket,
        tenant_id=tenant_id,
        user_id=user_id,
        metadata={
            "email": email,
            "role": role,
        }
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            message_type = message.get("type")
            if message_type == "ping":
                await websocket.send_json(
                    {"type": "pong", "timestamp": utc_now().isoformat()}
                )
            elif message_type == "pong":
                continue
            else:
                logger.debug(f"Unhandled websocket message: {message}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket error: {exc}")
        ws_manager.disconnect(websocket)

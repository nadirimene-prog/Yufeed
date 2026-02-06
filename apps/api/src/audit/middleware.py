"""
Audit logging middleware for append-only mutation tracking.
"""
import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import Request
from starlette.responses import Response

from src.auth.jwt_handler import JWTHandler
from src.audit.models import AuditLog
from src.database import SessionLocal, get_db

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
}

AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_BODY_BYTES = 100_000

ENTITY_ACTIONS = {
    "assign",
    "escalate",
    "close",
    "resolve",
    "triage",
    "batch",
    "approve",
    "reject",
    "login",
    "register",
    "refresh",
    "logout",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for key, val in value.items():
            if key.lower() in SENSITIVE_KEYS:
                redacted[key] = "***"
            else:
                redacted[key] = _redact(val)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _parse_json(body: bytes, content_type: str) -> Optional[Dict[str, Any]]:
    if "application/json" not in (content_type or ""):
        return None
    if len(body) > MAX_BODY_BYTES:
        return {"_truncated": True, "size": len(body)}
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def _extract_actor(request: Request) -> Dict[str, Optional[str]]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            payload = JWTHandler.decode_token(token)
            if JWTHandler.verify_token_type(payload, "access"):
                return {
                    "actor_id": payload.get("user_id"),
                    "actor_email": payload.get("sub"),
                    "actor_role": payload.get("role", "user"),
                    "actor_type": "user",
                    "tenant_id": payload.get("tenant_id"),
                }
        except Exception:
            logger.debug("Failed to decode JWT for audit logging", exc_info=True)

    return {
        "actor_id": None,
        "actor_email": None,
        "actor_role": None,
        "actor_type": "anonymous",
        "tenant_id": None,
    }


def _extract_entity(path: str) -> Dict[str, Optional[str]]:
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return {"entity_type": None, "entity_id": None}

    entity_type = None
    entity_id = None

    if parts[0] == "api" and len(parts) >= 2:
        entity_type = parts[1]
        if len(parts) >= 3 and parts[2] not in ENTITY_ACTIONS:
            entity_id = parts[2]

    return {"entity_type": entity_type, "entity_id": entity_id}


async def audit_log_middleware(request: Request, call_next) -> Response:
    if request.method not in AUDIT_METHODS:
        return await call_next(request)

    body = await request.body()
    request._body = body  # allow downstream to read body

    changes = _parse_json(body, request.headers.get("content-type", ""))
    if changes is not None:
        changes = _redact(changes)

    response: Response = await call_next(request)

    actor = _extract_actor(request)
    entity = _extract_entity(request.url.path)

    metadata = {
        "query": dict(request.query_params),
        "user_agent": request.headers.get("user-agent"),
    }

    audit_entry = AuditLog(
        audit_id=uuid.uuid4().hex,
        tenant_id=actor.get("tenant_id") or "default",
        actor_id=actor.get("actor_id"),
        actor_email=actor.get("actor_email"),
        actor_role=actor.get("actor_role"),
        actor_type=actor.get("actor_type"),
        actor_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        action=request.method.lower(),
        method=request.method,
        path=request.url.path,
        entity_type=entity.get("entity_type"),
        entity_id=entity.get("entity_id"),
        status_code=response.status_code,
        request_id=request.headers.get("x-request-id"),
        changes=changes,
        metadata_json=metadata,
    )

    try:
        override = request.app.dependency_overrides.get(get_db)
        if override:
            db_gen = override()
            db = next(db_gen)
        else:
            db = SessionLocal()

        db.add(audit_entry)
        db.commit()
    except Exception:
        logger.warning("Failed to write audit log entry", exc_info=True)
        if "db" in locals():
            db.rollback()
    finally:
        if "db" in locals():
            db.close()
        if "db_gen" in locals():
            try:
                next(db_gen)
            except StopIteration:
                pass

    return response

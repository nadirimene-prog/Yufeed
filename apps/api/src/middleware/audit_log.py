# apps/api/src/middleware/audit_log.py
import json
import uuid
from datetime import datetime, timezone
from fastapi import Request, Response


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
from starlette.middleware.base import BaseHTTPMiddleware
from src.database import AsyncSessionLocal
from src.models.audit import AuditLog

class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        body_bytes = await request.body()
        try:
            payload = json.loads(body_bytes) if body_bytes else {}
        except Exception:
            payload = {"raw": body_bytes.decode(errors="ignore")}

        for key in ("password", "secret", "token", "api_key"):
            if key in payload:
                payload[key] = "<redacted>"

        response: Response = await call_next(request)

        # ✅ Log the audit trail asynchronously without blocking/crashing the response
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    audit = AuditLog(
                        audit_id=request_id,
                        actor_id=getattr(request.state, "user", None).user_id
                        if hasattr(request.state, "user") else None,
                        actor_email=getattr(request.state, "user", None).email
                        if hasattr(request.state, "user") else None,
                        actor_role=getattr(request.state, "user", None).role
                        if hasattr(request.state, "user") else None,
                        action=request.method.lower(),
                        method=request.method,
                        path=request.url.path,
                        entity_type=request.headers.get("X-Entity-Type"),
                        entity_id=request.headers.get("X-Entity-Id"),
                        status_code=response.status_code,
                        changes=payload,
                        metadata_report={
                            "user_agent": request.headers.get("User-Agent"),
                            "ip": request.client.host,
                        },
                        created_at=utc_now(),
                    )
                    session.add(audit)
        except Exception as e:
            # Log the error but don't fail the request
            import logging
            logging.getLogger("uvicorn.error").error(f"Audit log failed: {e}")

        return response

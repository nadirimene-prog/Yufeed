# apps/api/src/middleware/audit_log.py
import json
import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.database import AsyncSessionLocal, get_db
from src.models.audit import AuditLog
from src.tenancy.context import get_current_tenant

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


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

        # ✅ Log the audit trail without crashing the response path.
        # In tests, prefer dependency overrides so audit writes land in the test DB.
        db_gen = None
        try:
            # Use tenant context set by TenantMiddleware (runs before audit log writes)
            tenant_id = get_current_tenant() or "default"

            entity_type = request.headers.get("X-Entity-Type")
            entity_id = request.headers.get("X-Entity-Id")

            if not entity_type and request.url.path.startswith("/api/alerts"):
                entity_type = "alerts"

            if not entity_id:
                match = re.match(r"^/api/alerts/([^/]+)", request.url.path)
                if match:
                    entity_id = match.group(1)

            audit = AuditLog(
                audit_id=request_id,
                tenant_id=tenant_id,
                actor_id=(
                    getattr(request.state, "user", None).user_id
                    if hasattr(request.state, "user")
                    else None
                ),
                actor_email=(
                    getattr(request.state, "user", None).email
                    if hasattr(request.state, "user")
                    else None
                ),
                actor_role=(
                    getattr(request.state, "user", None).role
                    if hasattr(request.state, "user")
                    else None
                ),
                actor_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                action=request.method.lower(),
                method=request.method,
                path=request.url.path,
                entity_type=entity_type,
                entity_id=entity_id,
                status_code=response.status_code,
                changes=payload,
                metadata_json={
                    "user_agent": request.headers.get("User-Agent"),
                    "ip": request.client.host,
                },
                created_at=utc_now(),
            )

            override = request.app.dependency_overrides.get(get_db)
            if override:
                db_gen = override()
                db = next(db_gen)
                db.add(audit)
                db.commit()
            else:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        session.add(audit)
        except Exception as e:
            logger.error(f"Audit log failed: {e}")
        finally:
            if db_gen is not None:
                try:
                    next(db_gen)
                except StopIteration:
                    pass

        return response

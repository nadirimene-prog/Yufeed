#!/usr/bin/env bash
# --------------------------------------------------------------
# apply‑yufeed‑patch.sh
# Run this *inside* the root of the cloned Yufeed repository.
# --------------------------------------------------------------

set -euo pipefail

# --------------------------------------------------------------
# 1️⃣  Replace / create source files
# --------------------------------------------------------------
cat > apps/api/src/main.py <<'PY'
# --------------------------------------------------------------
# Core FastAPI imports + OpenTelemetry + structured logging
# --------------------------------------------------------------
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import structlog
import time

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# --------------------------------------------------------------
# OpenTelemetry configuration (Console exporter – replace with OTLP in prod)
# --------------------------------------------------------------
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

import logging
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Existing imports (keep everything that was already here)
# ----------------------------------------------------------------------
from src.middleware import limiter, custom_rate_limit_handler, configure_redis_storage
from src.middleware.audit_log import AuditLogMiddleware
# <-- keep all your router imports that were already present in the file

# ----------------------------------------------------------------------
# FastAPI app – instrumented with OpenTelemetry
# ----------------------------------------------------------------------
app = FastAPI(
    title="EU Legal Monitoring MVP",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
FastAPIInstrumentor().instrument_app(app)

# Register the audit‑log middleware (runs on every request)
app.add_middleware(AuditLogMiddleware)

# ----------------------------------------------------------------------
# CORS & rate‑limiting (keep your existing configuration)
# ----------------------------------------------------------------------
# (your CORSMiddleware block stays unchanged)
# (your limiter block stays unchanged)

# ----------------------------------------------------------------------
# Light‑weight health‑check (used by Docker/K8s probes)
# ----------------------------------------------------------------------
@app.get("/healthz", tags=["monitoring"])
def health_check():
    return JSONResponse(
        content={"status": "ok", "service": "yufeed-api", "ts": int(time.time())}
    )

# ----------------------------------------------------------------------
# Global exception handler that also logs the error in JSON
# ----------------------------------------------------------------------
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    structlog.get_logger().error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc_msg=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ----------------------------------------------------------------------
# Register your routers (keep the same order you already had)
# ----------------------------------------------------------------------
# Example – copy the lines you already have:
# from src.api.auth import router as auth_router
# app.include_router(auth_router, prefix="/api")
# ... repeat for every router you imported ...
PY

cat > apps/api/requirements.txt <<'REQ'
fastapi
uvicorn
sqlalchemy
psycopg2-binary
alembic
redis
opensearch-py
httpx
feedparser
zeep
apscheduler
pydantic-settings
jinja2
python-multipart
python-jose[cryptography]
passlib[bcrypt]
slowapi
# NEW dependencies -------------------------------------------------
asyncpg
sqlmodel
opentelemetry-sdk
opentelemetry-api
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy
opentelemetry-exporter-otlp
structlog
prometheus-client
prometheus-fastapi-instrumentator
REQ

cat > apps/api/src/database.py <<'PY'
import logging
import os
from sqlalchemy import event, exc
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import Pool
from fastapi import HTTPException
from src.config import settings

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Async engine – uses asyncpg. DATABASE_URL must be in async form:
#   postgresql+asyncpg://user:pw@host:5432/db
# ----------------------------------------------------------------------
DATABASE_URL = settings.DATABASE_URL

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=Session,
    expire_on_commit=False,
)

# ----------------------------------------------------------------------
# Legacy sync engine – kept only for Alembic migrations (they run sync)
# ----------------------------------------------------------------------
sync_engine = create_engine(
    DATABASE_URL.replace("+asyncpg", ""),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

# ----------------------------------------------------------------------
# Connection‑pool monitoring – useful for Prometheus / Grafana alerts
# ----------------------------------------------------------------------
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    log.debug("Database connection established")

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    log.debug("Connection checked out from pool")

# ----------------------------------------------------------------------
# Async dependency – used by FastAPI routes
# ----------------------------------------------------------------------
async def get_async_db():
    """
    Async DB session dependency.
    All new endpoints should depend on ``Depends(get_async_db)``.
    """
    async with AsyncSessionLocal() as session:
        yield session

# ----------------------------------------------------------------------
# Sync dependency – retained for Alembic and any legacy scripts.
# ----------------------------------------------------------------------
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
PY

# auth dependencies – just swap the import
sed -i '' 's/from src\.database import get_db/from src.database import get_async_db/g' apps/api/src/auth/dependencies.py

# ------------------------------------------------------------------------------
# New middleware: audit_log.py
# ------------------------------------------------------------------------------
cat > apps/api/src/middleware/audit_log.py <<'PY'
# apps/api/src/middleware/audit_log.py
import json
import uuid
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.database import get_async_db
from src.models.audit import AuditLog   # model defined below

class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Records an immutable audit entry for every mutating HTTP request
    (POST, PUT, PATCH, DELETE).  Sensitive fields are redacted.
    """
    async def dispatch(self, request: Request, call_next):
        # Only record write‑type methods
        if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Read body (max 1 MiB)
        body_bytes = await request.body()
        try:
            payload = json.loads(body_bytes) if body_bytes else {}
        except Exception:
            payload = {"raw": body_bytes.decode(errors="ignore")}

        # Redact common secret keys
        for secret_key in ("password", "secret", "token", "api_key"):
            if secret_key in payload:
                payload[secret_key] = "<redacted>"

        response: Response = await call_next(request)

        async for db in get_async_db():
            audit = AuditLog(
                audit_id=request_id,
                actor_id=getattr(request.state, "user", None).user_id \
                    if hasattr(request.state, "user") else None,
                actor_email=getattr(request.state, "user", None).email \
                    if hasattr(request.state, "user") else None,
                actor_role=getattr(request.state, "user", None).role \
                    if hasattr(request.state, "user") else None,
                action=request.method.lower(),
                method=request.method,
                path=request.url.path,
                entity_type=request.headers.get("X-Entity-Type"),
                entity_id=request.headers.get("X-Entity-Id"),
                status_code=response.status_code,
                changes=payload,
                metadata_json={"user_agent": request.headers.get("User-Agent"),
                               "ip": request.client.host},
                created_at=datetime.utcnow(),
            )
            db.add(audit)
            await db.commit()
        return response
PY

# ------------------------------------------------------------------------------
# New router: metrics.py
# ------------------------------------------------------------------------------
cat > apps/api/src/monitoring/metrics.py <<'PY'
# apps/api/src/monitoring/metrics.py
from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator

router = APIRouter()
instrumentor = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
)

@router.on_event("startup")
def _setup_metrics():
    instrumentor.instrument()
    # the instrumentor registers /metrics automatically
    instrumentor.expose(app=None)
PY

# ------------------------------------------------------------------------------
# New service: feature_store.py
# ------------------------------------------------------------------------------
cat > apps/api/src/services/feature_store.py <<'PY'
# apps/api/src/services/feature_store.py
import json
import os
from typing import Dict, Any
import redis.asyncio as redis_async

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis = redis_async.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

CACHE_TTL = int(os.getenv("FEATURE_CACHE_TTL", "30"))

class FeatureStore:
    """
    Compute or fetch pre‑aggregated behavioural features for a user/event.
    The public method is async and returns a plain dict that can be merged
    into any downstream risk‑scoring pipeline.
    """
    @staticmethod
    async def compute_features(
        user_id: str,
        event_type: str,
        payload: Dict[str, Any],
        db,  # async Session from get_async_db()
    ) -> Dict[str, Any]:
        cache_key = f"feat:{user_id}:{event_type}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # ---- TODO: replace with real aggregation queries ----
        result = {
            "velocity_1h_count": 0,
            "velocity_1h_total": 0,
            "velocity_24h_count": 0,
            "velocity_24h_total": 0,
            "unique_countries_7d": 0,
            "unique_counterparties_30d": 0,
            "max_amount_30d": 0,
            "account_age_days": 0,
            "kyc_status": "unknown",
            "risk_level": "low",
        }

        await redis.set(cache_key, json.dumps(result), ex=CACHE_TTL)
        return result
PY

# ------------------------------------------------------------------------------
# New model: audit.py
# ------------------------------------------------------------------------------
cat > apps/api/src/models/audit.py <<'PY'
# apps/api/src/models/audit.py
from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(255), unique=True, nullable=False)
    actor_id = Column(String(255), nullable=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)
    actor_type = Column(String(50), nullable=True)
    actor_ip = Column(String(45), nullable=True)
    user_agent = Column(String, nullable=True)

    action = Column(String(50), nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)

    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    request_id = Column(String(255), nullable=True)

    changes = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
PY

# ------------------------------------------------------------------------------
# Alembic migration – you must replace <PREV_REV> with the revision
# of the migration that is currently newest in apps/api/alembic/versions/
# ------------------------------------------------------------------------------

# Find the latest revision automatically (fallback to manual if it fails)
PREV_REV=$(ls apps/api/alembic/versions/*.py | sort | tail -n1 | xargs -n1 basename | cut -d'_' -f1 | tr -d '"')
if [[ -z "$PREV_REV" ]]; then
  echo "⚠️ Could not auto‑detect previous revision. Please edit the file after this script finishes."
fi

cat > apps/api/alembic/versions/20240128_add_audit_logs.py <<PY
"""add immutable audit_logs

Revision ID: 20240128_add_audit_logs
Revises: $PREV_REV   # <-- replace with the ID you just saw (or edit later)
Create Date: 2024-01-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20240128_add_audit_logs"
down_revision = "$PREV_REV"   # <-- SAME value as above
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("audit_id", sa.String(255), nullable=False, unique=True),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("actor_role", sa.String(50), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("actor_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("changes", sa.JSON, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    # Immutable – any UPDATE/DELETE will raise an exception
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_mod()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_no_update
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_mod();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS audit_no_update ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_mod")
    op.drop_table("audit_logs")
PY

echo "✅ Files created/updated. If the migration’s down_revision is still <PREV_REV>, edit apps/api/alembic/versions/20240128_add_audit_logs.py and replace <PREV_REV> with the actual previous revision ID."

# --------------------------------------------------------------
# 2️⃣ Re‑build Docker images (installs new Python deps)
# --------------------------------------------------------------
echo "🔨 Re‑building Docker images (this may take a few minutes)…"
docker compose -f docker-compose.yml -f docker-compose.override.yml build

# --------------------------------------------------------------
# 3️⃣ Start the full stack (including monitoring)
# --------------------------------------------------------------
echo "🚀 Starting the stack (API + Prometheus + Grafana + Jaeger)…"
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# --------------------------------------------------------------
# 4️⃣ Wait for API health‑check
# --------------------------------------------------------------
echo "⏳ Waiting for the API to become healthy…"
until curl -s http://localhost:8000/healthz | grep -q '"status":"ok"'; do
  sleep 2
done
echo "✅ API is healthy!"

# --------------------------------------------------------------
# 5️⃣ Run the Alembic migration
# --------------------------------------------------------------
echo "🔧 Running Alembic migration to create audit_logs table…"
docker compose exec api alembic upgrade head

# --------------------------------------------------------------
# 6️⃣ Quick sanity checks
# --------------------------------------------------------------
echo "📊 Verifying /metrics endpoint:"
curl -s http://localhost:8000/metrics | head -n 5
echo ""

echo "🕵️‍♀️ Verifying a Jaeger trace (run a request now)…"
curl -s http://localhost:8000/healthz > /dev/null
echo "Open http://localhost:16686 in your browser – you should see a trace for GET /healthz."

echo "📝 Verifying audit log (POST request)…"
curl -X POST http://localhost:8000/api/alert \
  -H "Content-Type: application/json" \
  -d '{"title":"test"}' > /dev/null || true
echo "Now run:"
echo "   docker compose exec db psql -U postgres -d yufeed -c \"SELECT audit_id, path, action FROM audit_logs ORDER BY created_at DESC LIMIT 5;\""
echo ""
echo "✅ All steps completed. 🎉"

# --------------------------------------------------------------
# Core FastAPI imports + OpenTelemetry + structured logging
# --------------------------------------------------------------
from fastapi import FastAPI, Request
from .routers_autoload import register_routers
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import structlog
import time
import os
import logging

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

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Existing imports (keep everything that was already here)
# ----------------------------------------------------------------------
from src.middleware import limiter, custom_rate_limit_handler, configure_redis_storage
from src.middleware.audit_log import AuditLogMiddleware
from src.monitoring.metrics import setup_metrics
from src.config import settings
from src.tenancy.middleware import TenantMiddleware
from slowapi.errors import RateLimitExceeded

# ----------------------------------------------------------------------
# FastAPI app – instrumented with OpenTelemetry
# ----------------------------------------------------------------------
app = FastAPI(
    title="EU Legal Monitoring MVP",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# --- Rate limiter configuration ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

@app.on_event("startup")
async def startup_event():
    """Configure services on startup."""
    # Configure Redis for rate limiting (enables distributed rate limiting)
    if settings.REDIS_URL:
        configure_redis_storage(settings.REDIS_URL)
        logger.info(f"Rate limiter configured with Redis: {settings.REDIS_URL}")
    else:
        logger.warning("REDIS_URL not configured - rate limiting uses in-memory storage")

    # Ensure test DB schema exists for integration tests
    if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
        from src.database import Base, sync_engine
        Base.metadata.create_all(bind=sync_engine)

# --- OpenAPI alias for Swagger (/api/docs) ---
@app.get("/api/openapi.json", include_in_schema=False)
def _openapi_alias():
    return JSONResponse(app.openapi())




register_routers(app)

# Compatibility: expose compliance routes without /api prefix for legacy tests
from src.api.compliance import router as compliance_router
app.include_router(compliance_router)

# --- CORS Configuration ---
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
FastAPIInstrumentor().instrument_app(app)

# Register tenant context middleware before audit logging
app.add_middleware(TenantMiddleware)

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
from fastapi.exceptions import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    error_details = traceback.format_exc()
    structlog.get_logger().error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc_msg=str(exc),
        traceback=error_details
    )
    # Temporary: expose error details to UI for faster debugging
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": error_details if os.getenv("DEBUG", "true") == "true" else None
        },
    )

# ----------------------------------------------------------------------
# Register your routers (keep the same order you already had)
# ----------------------------------------------------------------------
# Example – copy the lines you already have:
# from src.api.auth import router as auth_router
# app.include_router(auth_router, prefix="/api")
# ... repeat for every router you imported ...


@app.get("/health", tags=["monitoring"])
async def health():
    return {"status": "ok", "v": "debug-1"}

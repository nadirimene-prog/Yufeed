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
from src.monitoring.logging_config import setup_logging, LoggingMiddleware
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
    # Ensure logging is configured before any other startup logs
    setup_logging()
    # Configure Redis for rate limiting (enables distributed rate limiting)
    if settings.REDIS_URL:
        configure_redis_storage(settings.REDIS_URL)
        logger.info(f"Rate limiter configured with Redis: {settings.REDIS_URL}")
    else:
        logger.warning("REDIS_URL not configured - rate limiting uses in-memory storage")

    if settings.POLICY_TEMPLATES_AUTO_SEED:
        try:
            from src.services.policy_templates import seed_policy_templates
            result = seed_policy_templates()
            logger.info(
                "Policy templates seeded: "
                f"{result.get('created', 0)} created, {result.get('updated', 0)} updated"
            )
            # Treat seeded templates as the canonical policy library: ensure one master PolicyDocument per template.
            from src.services.policy_library import ensure_master_policies
            master_result = ensure_master_policies()
            logger.info(
                "Master policies synced: "
                f"{master_result.get('created', 0)} created, "
                f"{master_result.get('updated', 0)} updated, "
                f"{master_result.get('duplicates_retired', 0)} duplicates retired"
            )
        except Exception as exc:
            logger.warning(f"Policy template seeding failed: {exc}")

    # Ensure test DB schema exists for integration tests
    if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
        from src.database import Base, sync_engine
        Base.metadata.create_all(bind=sync_engine)

# --- OpenAPI alias for Swagger (/api/docs) ---
@app.get("/api/openapi.json", include_in_schema=False)
def _openapi_alias():
    return JSONResponse(app.openapi())




register_routers(app)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
FastAPIInstrumentor().instrument_app(app)

# Register tenant context middleware before audit logging
app.add_middleware(TenantMiddleware)

# Log all requests with request/correlation IDs
app.add_middleware(LoggingMiddleware)

# Register the audit‑log middleware (runs on every request)
app.add_middleware(AuditLogMiddleware)

# --- CORS Configuration ---
# IMPORTANT: CORS must be added LAST so it runs FIRST (LIFO order)
# This ensures preflight OPTIONS requests are handled before other middleware
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
environment = os.getenv("ENVIRONMENT", "development").lower()
cors_kwargs = dict(
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dev ergonomics: Next dev sometimes shifts ports (3000 -> 3002, etc). If you're
# running locally, allow localhost/127.0.0.1 on any port + common LAN IPs.
if environment in {"development", "dev", "test", "testing"}:
    cors_kwargs["allow_origin_regex"] = os.getenv(
        "ALLOWED_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?$",
    )

app.add_middleware(CORSMiddleware, **cors_kwargs)

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

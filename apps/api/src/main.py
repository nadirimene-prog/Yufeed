# --------------------------------------------------------------
# Core FastAPI imports + OpenTelemetry + structured logging
# --------------------------------------------------------------
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from .routers_autoload import register_routers
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
import os
import logging

from src.middleware import limiter, custom_rate_limit_handler, configure_redis_storage
from src.middleware.audit_log import AuditLogMiddleware
from src.middleware.request_size import RequestSizeLimitMiddleware
from src.monitoring.logging_config import setup_logging, LoggingMiddleware
from src.config import settings
from src.tenancy.middleware import TenantMiddleware
from slowapi.errors import RateLimitExceeded

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# --------------------------------------------------------------
# OpenTelemetry configuration (Console exporter – replace with OTLP in prod)
# --------------------------------------------------------------
trace.set_tracer_provider(TracerProvider())
# Avoid BatchSpanProcessor in tests: it spawns a worker thread that can try to
# write to closed stdout/stderr after pytest exits.
if os.getenv("ENVIRONMENT", "development").lower() not in {"test", "testing"}:
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Lifespan – replaces deprecated @app.on_event("startup")
# ----------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure services on startup, clean up on shutdown."""
    setup_logging()

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

    if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
        from src.database import Base, sync_engine

        Base.metadata.create_all(bind=sync_engine)

    yield


# ----------------------------------------------------------------------
# FastAPI app – instrumented with OpenTelemetry
# ----------------------------------------------------------------------
from fastapi.security import OAuth2PasswordBearer

# OAuth2 scheme for Swagger UI authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scopes={
        "read": "Read access to resources",
        "write": "Write access to resources",
        "admin": "Administrative access"
    }
)

app = FastAPI(
    title="YuFeed API",
    description="AI-powered EU legal monitoring & AML compliance platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    # OpenAPI security scheme configuration
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "yufeed-api",
    },
)

# --- Rate limiter configuration ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


# --- OpenAPI schema customization ---
def custom_openapi():
    """Customize OpenAPI schema to include security schemes."""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>"
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Enter your API key (format: yk_live_<tenant_id>_<random>)"
        }
    }
    
    # Add global security requirement (can be overridden per endpoint)
    openapi_schema["security"] = [
        {"bearerAuth": []},
        {"apiKeyAuth": []}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


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

# Reject oversized request bodies before they reach audit logging or handlers
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=10 * 1024 * 1024)

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
# API Root & Versioning
# ----------------------------------------------------------------------
@app.get("/", tags=["root"])
def api_root():
    """
    API root endpoint showing available versions and documentation.

    Versioning Strategy:
    - /api/*     - Current stable version (backward compatible)
    - /api/v1/*  - Version 1 (explicit, identical to /api/*)
    - /api/v2/*  - Version 2 (future, for breaking changes)

    All existing endpoints are available at both /api/* and /api/v1/*
    """
    return {
        "message": "YuFeed API",
        "version": "1.0.0",
        "api_versions": {
            "current": {
                "path": "/api",
                "description": "Current stable API (backward compatible)",
                "deprecated": False,
            },
            "v1": {
                "path": "/api/v1",
                "description": "Version 1 API (explicit, identical to /api)",
                "deprecated": False,
            },
            "v2": {
                "path": "/api/v2",
                "description": "Version 2 API (reserved for future breaking changes)",
                "status": "not_yet_available",
            },
        },
        "documentation": {
            "swagger": "/api/docs",
            "redoc": "/api/redoc",
            "openapi_json": "/api/openapi.json",
        },
        "monitoring": {"health": "/healthz", "metrics": "/metrics"},
    }


# ----------------------------------------------------------------------
# Light‑weight health‑check (used by Docker/K8s probes)
# ----------------------------------------------------------------------
@app.get("/healthz", tags=["monitoring"])
def health_check():
    return JSONResponse(content={"status": "ok", "service": "yufeed-api", "ts": int(time.time())})


# ----------------------------------------------------------------------
# Global exception handlers
# ----------------------------------------------------------------------
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
        traceback=error_details,
    )
    is_debug = settings.ENVIRONMENT.lower() in {"development", "dev", "test", "testing"}
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__ if is_debug else None,
            "error_message": str(exc) if is_debug else None,
            "traceback": error_details if is_debug else None,
        },
    )

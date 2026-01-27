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

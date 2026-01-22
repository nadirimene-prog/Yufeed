from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from slowapi.errors import RateLimitExceeded
import os
import logging
from typing import List

from src.middleware import limiter, custom_rate_limit_handler, configure_redis_storage
from src.audit.middleware import audit_log_middleware
from src.monitoring.metrics import PrometheusMiddleware, metrics_endpoint, api_info
from src.monitoring.logging_config import setup_logging, LoggingMiddleware

# Initialize structured logging
setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EU Legal Monitoring MVP",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add rate limiter state to app
app.state.limiter = limiter

# Add rate limit exceeded exception handler
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


def validate_origins(origins_str: str) -> List[str]:
    """
    Validate and sanitize CORS origins from environment variable.

    Args:
        origins_str: Comma-separated list of allowed origins

    Returns:
        List of validated origin URLs

    Raises:
        ValueError: If invalid origin format detected in production
    """
    origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    validated_origins = []

    for origin in origins:
        # Check for valid URL format
        if not origin.startswith(("http://", "https://")):
            logger.warning(f"Invalid origin format (missing scheme): {origin}")
            continue

        # In production, reject wildcards
        if "*" in origin and os.getenv("ENVIRONMENT", "development") == "production":
            logger.error(f"Wildcard origins not allowed in production: {origin}")
            raise ValueError(
                "Wildcard CORS origins are not allowed in production environment"
            )

        # Reject suspicious patterns
        if origin.count("://") > 1:
            logger.warning(f"Suspicious origin format (multiple schemes): {origin}")
            continue

        # Validate localhost only in development
        if "localhost" in origin or "127.0.0.1" in origin:
            if os.getenv("ENVIRONMENT", "development") == "production":
                logger.warning(f"Localhost origin rejected in production: {origin}")
                continue

        validated_origins.append(origin)
        logger.info(f"CORS origin allowed: {origin}")

    if not validated_origins:
        # Fallback to safe defaults for development
        default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        logger.warning(
            f"No valid origins configured, using defaults: {default_origins}"
        )
        return default_origins

    return validated_origins


# Get and validate allowed origins
try:
    ALLOWED_ORIGINS = validate_origins(
        os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    )
except ValueError as e:
    logger.critical(f"CORS configuration error: {e}")
    # In production, fail fast with invalid CORS config
    if os.getenv("ENVIRONMENT") == "production":
        raise
    # In development, use safe defaults
    ALLOWED_ORIGINS = ["http://localhost:3000"]

# Add CORS middleware with validated origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization"],  # Explicit headers
    expose_headers=["X-Request-ID"],
)


# Request Size Limit Middleware (prevent DoS attacks)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """
    Limit request body size to prevent DoS attacks.

    Maximum sizes:
    - Default: 10MB for most requests
    - File uploads: Should use streaming (not covered here)
    """
    max_size = int(os.getenv("MAX_REQUEST_SIZE", 10 * 1024 * 1024))  # 10MB default

    content_length = request.headers.get("content-length")

    if content_length:
        content_length = int(content_length)
        if content_length > max_size:
            logger.warning(
                f"Request size {content_length} bytes exceeds limit {max_size} bytes"
            )
            return Response(
                content="Request body too large",
                status_code=413,
                headers={"Retry-After": "3600"}  # Suggest retry after 1 hour
            )

    return await call_next(request)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:*"
    )

    # Strict Transport Security (HTTPS only - enable in production)
    if os.getenv("ENABLE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    return response

# Monitoring middleware - Prometheus metrics
app.add_middleware(PrometheusMiddleware)

# Logging middleware - structured logging with request IDs
app.add_middleware(LoggingMiddleware)

# Audit logging middleware (append-only for mutations)
app.middleware("http")(audit_log_middleware)

# Metrics endpoint
@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/cache/stats")
def cache_stats():
    """Cache statistics and effectiveness monitoring"""
    from src.cache.cache_warmer import cache_warmer
    return cache_warmer.get_cache_stats()

@app.on_event("startup")
def startup_event():
    from src.database import engine, Base
    from src.search import init_indices
    from src.config import settings
    import os

    # Set API info metric
    version = os.getenv("API_VERSION", "1.0.0")
    environment = os.getenv("ENVIRONMENT", "development")
    api_info.labels(version=version, environment=environment).set(1)

    logger.info("Starting YuFeed API", version=version, environment=environment)

    # Setup distributed tracing
    try:
        from src.monitoring.tracing import setup_tracing
        setup_tracing(app, engine)
    except Exception as e:
        logger.warning(f"Failed to setup tracing: {e}")

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Init search
    try:
        init_indices()
    except Exception as e:
        logger.warning("OpenSearch initialization failed", error=str(e))

    # Configure rate limiter with Redis (if available)
    try:
        redis_url = getattr(settings, "REDIS_URL", None)
        if redis_url:
            configure_redis_storage(redis_url)
            logger.info("Rate limiter configured with Redis backend")
        else:
            logger.warning("Redis URL not configured, using in-memory rate limiting")
    except Exception as e:
        logger.warning(f"Failed to configure Redis for rate limiting: {e}. Using in-memory storage.")

    # Warm up cache
    try:
        from src.cache.cache_warmer import cache_warmer
        cache_warmer.warm_all()
    except Exception as e:
        logger.warning(f"Cache warming failed: {e}")

from src.api.auth import router as auth_router
from src.api.endpoints import router as api_router
from src.api.compliance import router as compliance_router
from src.api.impact import router as impact_router
from src.api.query import router as query_router
from src.api.transactions import router as transactions_router
from src.api.alerts import router as alerts_router
from src.api.monitoring_dashboard import router as monitoring_router
from src.api.ai_agents import router as ai_agents_router
from src.api.cases import router as cases_router
from src.api.risk_profiles import router as risk_profiles_router
from src.api.monitoring_rules import router as monitoring_rules_router
from src.api.network_analysis import router as network_router
from src.api.reporting import router as reporting_router
from src.api.celex import router as celex_router
from src.api.aml_officer import router as aml_officer_router
from src.api.audit import router as audit_router
from src.api.features import router as features_router
from src.api.decisioning import router as decisioning_router
from src.api.onchain_risk import router as onchain_router
from src.api.travel_rule import router as travel_rule_router
from src.api.model_registry import router as model_registry_router

# Register authentication routes first
app.include_router(auth_router, prefix="/api")

# Register other routes
app.include_router(api_router)
app.include_router(compliance_router)
app.include_router(impact_router)
app.include_router(query_router)
app.include_router(transactions_router)
app.include_router(alerts_router)
app.include_router(monitoring_router)
app.include_router(ai_agents_router)
app.include_router(cases_router)
app.include_router(risk_profiles_router)
app.include_router(monitoring_rules_router)
app.include_router(network_router)
app.include_router(reporting_router)
app.include_router(celex_router)
app.include_router(aml_officer_router)
app.include_router(audit_router)
app.include_router(features_router)
app.include_router(decisioning_router)
app.include_router(onchain_router)
app.include_router(travel_rule_router)
app.include_router(model_registry_router)

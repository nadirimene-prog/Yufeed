"""
Rate Limiting Middleware

Provides configurable rate limiting for API endpoints to prevent abuse.
Uses slowapi (FastAPI port of Flask-Limiter) with Redis backend for distributed rate limiting.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

import logging
import os

logger = logging.getLogger(__name__)
_IS_TEST_ENV = os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}


def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.

    Uses authenticated user ID if available, otherwise falls back to IP address.
    This allows for more accurate rate limiting per user.

    Args:
        request: FastAPI request object

    Returns:
        Unique identifier string (user_id or IP address)
    """
    # Try to get user from request state (set by authentication middleware)
    if hasattr(request.state, "user") and request.state.user:
        user_id = getattr(request.state.user, "user_id", None)
        if user_id:
            logger.debug(f"Rate limiting by user_id: {user_id}")
            return f"user:{user_id}"

    # Fall back to IP address
    ip_address = get_remote_address(request)
    logger.debug(f"Rate limiting by IP: {ip_address}")
    return f"ip:{ip_address}"


# Initialize rate limiter
# Default storage is in-memory, but for production use Redis
limiter = Limiter(
    key_func=get_identifier,
    default_limits=["200 per hour", "1000 per day"],
    storage_uri="memory://",  # Change to "redis://localhost:6379" in production
    strategy="fixed-window",
)


# Custom rate limit exceeded handler
def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors.

    Logs the violation and returns a user-friendly error response.
    """
    identifier = get_identifier(request)
    logger.warning(
        f"Rate limit exceeded for {identifier} on {request.url.path}. " f"Limit: {exc.detail}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": exc.detail,
            "retry_after": getattr(exc, "retry_after", None),
        },
    )


# Pre-configured rate limit decorators for common use cases
class RateLimits:
    """Common rate limit configurations for different endpoint types."""

    # Authentication endpoints (stricter limits to prevent brute force)
    AUTH_LOGIN = "20 per minute" if _IS_TEST_ENV else "5 per minute"
    AUTH_REGISTER = "10 per hour" if _IS_TEST_ENV else "3 per hour"
    AUTH_REFRESH = "60 per minute" if _IS_TEST_ENV else "10 per minute"
    AUTH_FORGOT_PASS = "20 per minute" if _IS_TEST_ENV else "3 per minute"
    AUTH_RESET_PASS = "20 per minute" if _IS_TEST_ENV else "5 per minute"

    # Search and query endpoints
    SEARCH = "30 per minute"  # 30 searches per minute
    QUERY = "60 per minute"  # 60 queries per minute

    # Data modification endpoints
    CREATE = "20 per minute"  # 20 creates per minute
    UPDATE = "30 per minute"  # 30 updates per minute
    DELETE = "10 per minute"  # 10 deletes per minute

    # Read endpoints (more permissive)
    READ = "100 per minute"  # 100 reads per minute
    LIST = "60 per minute"  # 60 list operations per minute

    # AI/LLM endpoints (expensive operations)
    AI_ANALYSIS = "10 per hour"  # 10 AI analyses per hour
    AI_GENERATION = "5 per hour"  # 5 AI generations per hour

    # Export/reporting endpoints (resource intensive)
    EXPORT = "5 per hour"  # 5 exports per hour
    REPORT = "10 per hour"  # 10 reports per hour


def configure_redis_storage(redis_url: str):
    """
    Configure rate limiter to use Redis for distributed rate limiting.

    Call this function in main.py startup event with Redis URL from config.

    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379")

    Example:
        >>> configure_redis_storage(settings.REDIS_URL)
    """
    global limiter
    limiter.storage_uri = redis_url
    logger.info(f"Rate limiter configured with Redis storage: {redis_url}")

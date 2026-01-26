"""
Structured logging configuration using structlog.
Phase 4A: Task 2.2 - Structured Logging
"""
import logging
import sys
from typing import Any, Dict
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    structlog = None
    STRUCTLOG_AVAILABLE = False

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    jsonlogger = None
    JSON_LOGGER_AVAILABLE = False
from contextvars import ContextVar
from datetime import datetime

# Context variables for correlation IDs
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


# ============================================================================
# STRUCTLOG CONFIGURATION
# ============================================================================

def add_app_context(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add application context to log events.
    """
    # Add request and correlation IDs from context
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id

    correlation_id = correlation_id_ctx.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id

    user_id = user_id_ctx.get()
    if user_id:
        event_dict["user_id"] = user_id

    # Add service information
    event_dict["service"] = "yufeed-api"
    event_dict["environment"] = get_environment()

    return event_dict


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add ISO 8601 timestamp to log events.
    """
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_log_level(
    logger: logging.Logger, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add log level to event dict.
    """
    if method_name == "warning":
        event_dict["level"] = "warn"
    else:
        event_dict["level"] = method_name
    return event_dict


def get_environment() -> str:
    """
    Get current environment from settings or environment variable.
    """
    import os
    return os.getenv("ENVIRONMENT", "development")


def configure_structlog():
    """
    Configure structlog for structured JSON logging.
    """
    if not STRUCTLOG_AVAILABLE:
        return
    # Determine if running in production
    is_production = get_environment() == "production"

    # Configure processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_log_level,
        add_timestamp,
        add_app_context,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        # Use JSON renderer for production (machine-readable)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Use console renderer for development (human-readable)
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_stdlib_logging():
    """
    Configure standard library logging to work with structlog.
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Set log level based on environment
    environment = get_environment()
    if environment == "production":
        log_level = logging.INFO
    elif environment == "test":
        log_level = logging.WARNING
    else:
        log_level = logging.DEBUG

    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler with JSON formatter for production
    handler = logging.StreamHandler(sys.stdout)

    if environment == "production" and JSON_LOGGER_AVAILABLE:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={
                "levelname": "level",
                "name": "logger",
                "asctime": "timestamp"
            }
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure specific loggers
    # Reduce noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def setup_logging():
    """
    Main function to set up all logging configuration.
    Call this at application startup.
    """
    _patch_logger_for_kwargs()
    configure_stdlib_logging()
    configure_structlog()


def _patch_logger_for_kwargs():
    """
    Allow stdlib loggers to accept extra keyword arguments without crashing.
    """
    if getattr(logging.Logger._log, "_yufeed_kwargs_patch", False):
        return

    original_log = logging.Logger._log

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
        if kwargs:
            msg = f"{msg} | {kwargs}"
        return original_log(
            self,
            level,
            msg,
            args,
            exc_info=exc_info,
            extra=extra,
            stack_info=stack_info,
            stacklevel=stacklevel,
        )

    _log._yufeed_kwargs_patch = True
    logging.Logger._log = _log


# ============================================================================
# LOGGING HELPERS
# ============================================================================

class _FallbackLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _log(self, level: int, event: str, **kwargs: Any):
        if kwargs:
            event = f"{event} | {kwargs}"
        self._logger.log(level, event)

    def info(self, event: str, **kwargs: Any):
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any):
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any):
        exc_info = kwargs.pop("exc_info", False)
        if kwargs:
            event = f"{event} | {kwargs}"
        self._logger.error(event, exc_info=exc_info)


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("user_login", user_id="12345", ip_address="1.2.3.4")
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return _FallbackLogger(name)


def set_request_id(request_id: str):
    """
    Set request ID in context for all subsequent logs.
    """
    request_id_ctx.set(request_id)


def set_correlation_id(correlation_id: str):
    """
    Set correlation ID for distributed tracing.
    """
    correlation_id_ctx.set(correlation_id)


def set_user_id(user_id: str):
    """
    Set user ID in context for all subsequent logs.
    """
    user_id_ctx.set(user_id)


def clear_context():
    """
    Clear all context variables.
    Should be called at the end of request handling.
    """
    request_id_ctx.set("")
    correlation_id_ctx.set("")
    user_id_ctx.set("")


# ============================================================================
# LOGGING MIDDLEWARE
# ============================================================================

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import uuid
import time


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request/correlation IDs and log all requests.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        set_request_id(request_id)

        # Extract or generate correlation ID for distributed tracing
        correlation_id = request.headers.get("x-correlation-id", request_id)
        set_correlation_id(correlation_id)

        # Extract user ID from JWT if available (will be set by auth middleware)
        # For now, we'll leave it empty and let auth middleware set it

        logger = get_logger(__name__)

        # Log request
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=round(duration, 3),
            )

            # Add request ID to response headers
            response.headers["x-request-id"] = request_id
            response.headers["x-correlation-id"] = correlation_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_seconds=round(duration, 3),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

            raise

        finally:
            # Clear context
            clear_context()


# ============================================================================
# LOG SAMPLING (for high-traffic endpoints)
# ============================================================================

import random


class SampledLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that samples logs based on sampling rate to reduce volume.
    Useful for very high-traffic endpoints.
    """

    def __init__(self, app, sample_rate: float = 0.1):
        """
        Initialize with sampling rate (0.0 to 1.0).
        1.0 = log all requests, 0.1 = log 10% of requests.
        """
        super().__init__(app)
        self.sample_rate = sample_rate

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Always log errors, sample success
        should_log = random.random() < self.sample_rate

        if should_log:
            return await LoggingMiddleware(self.app).dispatch(request, call_next)
        else:
            return await call_next(request)

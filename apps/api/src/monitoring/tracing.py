"""
OpenTelemetry distributed tracing configuration.
Phase 4A: Task 2.3 - OpenTelemetry Tracing
"""

import logging
import os

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    TRACE_AVAILABLE = True
except ImportError:
    trace = None
    TRACE_AVAILABLE = False

logger = logging.getLogger(__name__)


def setup_tracing(app, engine):
    """
    Configure OpenTelemetry tracing with Jaeger exporter.

    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine instance
    """
    if not TRACE_AVAILABLE:
        logger.warning("OpenTelemetry not installed; tracing disabled")
        return
    try:
        # Get configuration from environment
        service_name = os.getenv("SERVICE_NAME", "yufeed-api")
        service_version = os.getenv("API_VERSION", "1.0.0")
        jaeger_host = os.getenv("JAEGER_HOST", "localhost")
        jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))
        environment = os.getenv("ENVIRONMENT", "development")

        # Create resource with service information
        resource = Resource(
            attributes={
                SERVICE_NAME: service_name,
                SERVICE_VERSION: service_version,
                "environment": environment,
                "deployment.environment": environment,
            }
        )

        # Configure tracer provider
        provider = TracerProvider(resource=resource)

        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        # Add span processor
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented for tracing")

        # Auto-instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
            commenter_options={"db_framework": True, "opentelemetry_values": True},
        )
        logger.info("SQLAlchemy instrumented for tracing")

        # Auto-instrument HTTPX (for external API calls)
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumented for tracing")

        # Auto-instrument Redis
        try:
            RedisInstrumentor().instrument()
            logger.info("Redis instrumented for tracing")
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")

        logger.info(
            f"OpenTelemetry tracing configured: "
            f"service={service_name}, jaeger={jaeger_host}:{jaeger_port}"
        )

    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}", exc_info=True)
        # Don't fail startup if tracing setup fails
        logger.warning("Continuing without distributed tracing")


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for creating custom spans.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        Tracer instance

    Usage:
        from src.monitoring.tracing import get_tracer

        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("custom_operation") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("operation_type", "risk_calculation")
            # ... do work ...
    """
    if not TRACE_AVAILABLE:
        return _NoopTracer()
    return trace.get_tracer(name)


# ============================================================================
# CUSTOM SPAN DECORATORS
# ============================================================================

from functools import wraps
from typing import Callable, Optional


def traced(span_name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    Decorator to create a custom span for a function.

    Args:
        span_name: Name of the span (default: function name)
        attributes: Additional attributes to add to span

    Usage:
        @traced(span_name="calculate_risk_score")
        def calculate_risk(transaction: dict) -> float:
            return risk_score

        @traced(attributes={"service": "rules_engine"})
        def evaluate_rule(rule_id: str) -> bool:
            return result
    """

    def decorator(func: Callable) -> Callable:
        if not TRACE_AVAILABLE:
            return func

        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add function arguments as attributes (be careful with sensitive data)
                # Uncomment if needed:
                # if args:
                #     span.set_attribute("args_count", len(args))
                # if kwargs:
                #     for key in kwargs:
                #         if key not in ["password", "token", "secret"]:
                #             span.set_attribute(f"arg.{key}", str(kwargs[key]))

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result

                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error", str(e))
                    span.set_attribute("error_type", type(e).__name__)
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


# ============================================================================
# TRACING UTILITIES
# ============================================================================


def add_span_attributes(attributes: dict):
    """
    Add attributes to the current active span.

    Args:
        attributes: Dictionary of attributes to add

    Usage:
        from src.monitoring.tracing import add_span_attributes

        def process_transaction(txn_id: str):
            add_span_attributes({
                "transaction_id": txn_id,
                "amount": 1000.50,
                "currency": "USD"
            })
    """
    if not TRACE_AVAILABLE:
        return
    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[dict] = None):
    """
    Add an event to the current active span.

    Args:
        name: Event name
        attributes: Event attributes

    Usage:
        from src.monitoring.tracing import add_span_event

        add_span_event("rule_matched", {
            "rule_id": "rule_001",
            "rule_name": "High Value Transaction"
        })
    """
    if not TRACE_AVAILABLE:
        return
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes=attributes or {})


def record_exception(exception: Exception):
    """
    Record an exception in the current span.

    Args:
        exception: The exception to record
    """
    if not TRACE_AVAILABLE:
        return
    span = trace.get_current_span()
    if span:
        span.record_exception(exception)
        span.set_attribute("error", str(exception))
        span.set_attribute("error_type", type(exception).__name__)


class _NoopSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_attribute(self, *args, **kwargs):
        return None

    def record_exception(self, *args, **kwargs):
        return None

    def add_event(self, *args, **kwargs):
        return None


class _NoopTracer:
    def start_as_current_span(self, *args, **kwargs):
        return _NoopSpan()

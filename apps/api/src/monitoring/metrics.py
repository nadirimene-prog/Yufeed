"""
Prometheus metrics definitions and middleware.
Phase 4A: Task 2.1 - Prometheus Metrics Integration
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class _NoOpMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

    def Counter(*args, **kwargs):
        return _NoOpMetric()

    def Histogram(*args, **kwargs):
        return _NoOpMetric()

    def Gauge(*args, **kwargs):
        return _NoOpMetric()

    def generate_latest():
        return b"# prometheus metrics disabled\n"


# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

# Request counters
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_requests_errors = Counter(
    "http_requests_errors_total",
    "Total HTTP request errors",
    ["method", "endpoint", "error_type"]
)

# Response time histograms (in seconds)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

# Database metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections"
)

db_connections_total = Counter(
    "db_connections_total",
    "Total database connections created"
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Redis metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"]
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"]
)

# Business metrics
transactions_ingested_total = Counter(
    "transactions_ingested_total",
    "Total transactions ingested",
    ["status"]
)

alerts_created_total = Counter(
    "alerts_created_total",
    "Total alerts created",
    ["alert_type", "severity"]
)

alerts_resolved_total = Counter(
    "alerts_resolved_total",
    "Total alerts resolved",
    ["resolution_status"]
)

cases_opened_total = Counter(
    "cases_opened_total",
    "Total cases opened",
    ["case_type", "priority"]
)

rules_evaluated_total = Counter(
    "rules_evaluated_total",
    "Total rules evaluated",
    ["rule_category"]
)

rules_triggered_total = Counter(
    "rules_triggered_total",
    "Total rules triggered",
    ["rule_id", "rule_category"]
)

# Queue metrics
celery_tasks_queued = Gauge(
    "celery_tasks_queued",
    "Number of tasks in Celery queue",
    ["queue_name"]
)

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"]
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution duration",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

# OpenSearch metrics
opensearch_queries_total = Counter(
    "opensearch_queries_total",
    "Total OpenSearch queries",
    ["index", "status"]
)

opensearch_query_duration_seconds = Histogram(
    "opensearch_query_duration_seconds",
    "OpenSearch query duration",
    ["index"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# WebSocket metrics (for Phase 4B)
websocket_connections_active = Gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections"
)

websocket_messages_sent_total = Counter(
    "websocket_messages_sent_total",
    "Total WebSocket messages sent",
    ["event_type"]
)

# System metrics
api_info = Gauge(
    "api_info",
    "API version info",
    ["version", "environment"]
)


# ============================================================================
# PROMETHEUS METRICS MIDDLEWARE
# ============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track Prometheus metrics for all HTTP requests.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Normalize path to avoid high cardinality
        # Replace IDs with placeholders
        endpoint = self._normalize_path(path)

        # Track request start time
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            status = response.status_code

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Track errors
            if status >= 400:
                error_type = self._get_error_type(status)
                http_requests_errors.labels(
                    method=method,
                    endpoint=endpoint,
                    error_type=error_type
                ).inc()

            return response

        except Exception as e:
            # Track exceptions
            duration = time.time() - start_time

            http_requests_errors.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(e).__name__
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            raise

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Normalize path to reduce cardinality by replacing IDs with placeholders.
        """
        parts = path.split("/")
        normalized_parts = []

        for part in parts:
            # Replace UUIDs and numeric IDs
            if part.isdigit() or (
                len(part) == 36 and part.count("-") == 4  # UUID format
            ) or (
                part.startswith("ALT-") or part.startswith("CSE-") or part.startswith("TXN-")
            ):
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)

        return "/".join(normalized_parts)

    @staticmethod
    def _get_error_type(status_code: int) -> str:
        """
        Categorize HTTP error by status code.
        """
        if status_code == 400:
            return "bad_request"
        elif status_code == 401:
            return "unauthorized"
        elif status_code == 403:
            return "forbidden"
        elif status_code == 404:
            return "not_found"
        elif status_code == 422:
            return "validation_error"
        elif status_code == 429:
            return "rate_limit_exceeded"
        elif 400 <= status_code < 500:
            return "client_error"
        elif status_code == 500:
            return "internal_server_error"
        elif status_code == 503:
            return "service_unavailable"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown"


# ============================================================================
# METRICS ENDPOINT
# ============================================================================

def metrics_endpoint() -> Response:
    """
    Endpoint to expose Prometheus metrics.
    """
    if not PROMETHEUS_AVAILABLE:
        return Response(content="metrics disabled\n", media_type="text/plain")
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_transaction_ingestion(status: str = "success"):
    """Record a transaction ingestion event."""
    transactions_ingested_total.labels(status=status).inc()


def record_alert_creation(alert_type: str, severity: str):
    """Record an alert creation event."""
    alerts_created_total.labels(alert_type=alert_type, severity=severity).inc()


def record_alert_resolution(resolution_status: str):
    """Record an alert resolution event."""
    alerts_resolved_total.labels(resolution_status=resolution_status).inc()


def record_case_opened(case_type: str, priority: str):
    """Record a case opening event."""
    cases_opened_total.labels(case_type=case_type, priority=priority).inc()


def record_rule_evaluation(rule_category: str):
    """Record a rule evaluation event."""
    rules_evaluated_total.labels(rule_category=rule_category).inc()


def record_rule_triggered(rule_id: str, rule_category: str):
    """Record a rule trigger event."""
    rules_triggered_total.labels(rule_id=rule_id, rule_category=rule_category).inc()


def record_cache_hit(cache_type: str):
    """Record a cache hit."""
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str):
    """Record a cache miss."""
    cache_misses_total.labels(cache_type=cache_type).inc()

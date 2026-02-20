from prometheus_client import Gauge, Counter, Histogram

# apps/api/src/monitoring/metrics.py
from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator

# ============================================================================
# WebSocket Metrics
# ============================================================================

websocket_connections_active = Gauge(
    "websocket_connections_active", "Number of active websocket connections"
)

router = APIRouter()

websocket_messages_sent_total = Counter(
    "websocket_messages_sent_total",
    "Total number of websocket messages sent",
    ["event_type"],
)

# ============================================================================
# Cache Metrics
# ============================================================================

cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
)

cache_hit_rate = Gauge("cache_hit_rate", "Cache hit rate (hits / total)", ["cache_type"])

cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation duration",
    ["cache_type", "operation"],  # operation: "get", "set", "delete"
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)

# ============================================================================
# Feature Store Metrics
# ============================================================================

feature_extraction_duration_seconds = Histogram(
    "feature_extraction_duration_seconds",
    "Feature extraction duration",
    ["feature_type"],  # "user", "transaction", etc.
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

feature_cache_hits_total = Counter("feature_cache_hits_total", "Feature cache hits")

feature_cache_misses_total = Counter("feature_cache_misses_total", "Feature cache misses")

feature_staleness_seconds = Histogram(
    "feature_staleness_seconds",
    "Time since feature last updated",
    ["tenant_id", "entity_type"],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400],
)

# ============================================================================
# Transaction Processing Metrics
# ============================================================================

transaction_processing_duration_seconds = Histogram(
    "transaction_processing_duration_seconds",
    "Transaction processing duration",
    ["status"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

transaction_processing_total = Counter(
    "transaction_processing_total", "Total transactions processed", ["tenant_id", "status"]
)

# ============================================================================
# Rules Engine Metrics
# ============================================================================

rule_coercion_failures_total = Counter(
    "rule_coercion_failures_total",
    "Total number of rule numeric coercion failures",
    ["rule_id", "field"],
)

rule_evaluations_total = Counter(
    "rule_evaluations_total", "Total rule evaluations", ["tenant_id", "rule_id", "matched"]
)

# ============================================================================
# AI API Cost Metrics
# ============================================================================

ai_api_calls_total = Counter(
    "ai_api_calls_total", "AI API calls", ["provider", "model", "tenant_id"]
)

ai_api_tokens_used_total = Counter(
    "ai_api_tokens_used_total",
    "Tokens used",
    ["provider", "model", "tenant_id", "token_type"],  # token_type: "prompt" or "completion"
)

ai_api_cost_usd = Counter(
    "ai_api_cost_usd", "Estimated cost in USD", ["provider", "model", "tenant_id"]
)

# ============================================================================
# DLQ Metrics
# ============================================================================

dlq_size_gauge = Gauge("dlq_size", "Number of items in Dead Letter Queue", ["tenant_id"])

# ============================================================================
# Compliance Pipeline Metrics
# ============================================================================

obligations_created_total = Counter(
    "obligations_created_total",
    "Total obligations created by ingestion pipeline",
    ["source", "confidence_tier"],
)

policy_mapping_suggestions_total = Counter(
    "policy_mapping_suggestions_total",
    "Total policy mapping suggestions created",
    ["match_method"],
)

obligation_approval_total = Counter(
    "obligation_approval_total",
    "Total obligation approval operations",
    ["status"],
)

instrumentor = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
)


@router.on_event("startup")
def _setup_metrics():
    # disabled: metrics are now attached via setup_metrics(app) in main.py
    return


# ----------------------------------------------------------------------
# Cache metrics (used by cache_manager.py)
# ----------------------------------------------------------------------
def record_cache_hit(key: str):
    """Record a cache hit for the given cache_type."""
    try:
        cache_hits_total.labels(cache_type=key).inc()
    except Exception:
        # Metrics must never break the request path.
        return


def record_cache_miss(key: str):
    """Record a cache miss for the given cache_type."""
    try:
        cache_misses_total.labels(cache_type=key).inc()
    except Exception:
        return


def setup_metrics(app):
    """Attach Prometheus instrumentation to the FastAPI app."""
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

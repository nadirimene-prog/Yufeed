from prometheus_client import Gauge, Counter
# apps/api/src/monitoring/metrics.py
from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator

websocket_connections_active = Gauge(
    "websocket_connections_active",
    "Number of active websocket connections"
)

router = APIRouter()
websocket_messages_sent_total = Counter(
    "websocket_messages_sent_total",
    "Total number of websocket messages sent",
    ["event_type"],
)

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

rule_coercion_failures_total = Counter(
    "rule_coercion_failures_total",
    "Total number of rule numeric coercion failures",
    ["rule_id", "field"],
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

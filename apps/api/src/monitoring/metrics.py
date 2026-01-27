# apps/api/src/monitoring/metrics.py
from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator

router = APIRouter()
instrumentor = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
)

@router.on_event("startup")
def _setup_metrics():
    instrumentor.instrument()
    # the instrumentor registers /metrics automatically
    instrumentor.expose(app=None)

# ----------------------------------------------------------------------
# Cache metrics (used by cache_manager.py)
# ----------------------------------------------------------------------
def record_cache_hit(key: str):
    """Record a cache hit (stub – replace with real Prometheus counter)."""
    pass

def record_cache_miss(key: str):
    """Record a cache miss (stub – replace with real Prometheus counter)."""
    pass

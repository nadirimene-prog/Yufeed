# apps/api/src/services/feature_store.py
import json
import os
from typing import Dict, Any
import redis.asyncio as redis_async

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis = redis_async.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

CACHE_TTL = int(os.getenv("FEATURE_CACHE_TTL", "30"))

class FeatureStore:
    """
    Compute or fetch pre‑aggregated behavioural features for a user/event.
    The public method is async and returns a plain dict that can be merged
    into any downstream risk‑scoring pipeline.
    """
    @staticmethod
    async def compute_features(
        user_id: str,
        event_type: str,
        payload: Dict[str, Any],
        db,  # async Session from get_async_db()
    ) -> Dict[str, Any]:
        cache_key = f"feat:{user_id}:{event_type}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # ---- TODO: replace with real aggregation queries ----
        result = {
            "velocity_1h_count": 0,
            "velocity_1h_total": 0,
            "velocity_24h_count": 0,
            "velocity_24h_total": 0,
            "unique_countries_7d": 0,
            "unique_counterparties_30d": 0,
            "max_amount_30d": 0,
            "account_age_days": 0,
            "kyc_status": "unknown",
            "risk_level": "low",
        }

        await redis.set(cache_key, json.dumps(result), ex=CACHE_TTL)
        return result

# --- Compatibility alias (required by src.api.features) ---
FeatureStoreService = FeatureStore


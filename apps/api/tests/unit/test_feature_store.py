import json
import pytest

from src.services import feature_store


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feature_store_compute(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(feature_store, "redis", fake)

    result = await feature_store.FeatureStore.compute_features(
        "user1", "event", {"x": 1}, db=None
    )
    assert result["kyc_status"] == "unknown"

    # Cached path
    cached = await feature_store.FeatureStore.compute_features(
        "user1", "event", {"x": 1}, db=None
    )
    assert cached["kyc_status"] == "unknown"

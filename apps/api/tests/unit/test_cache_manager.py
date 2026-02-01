import pytest
import fnmatch

from src.cache.cache_manager import CacheManager, cached, cache_aside


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl
        return True

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                self.ttls.pop(key, None)
                deleted += 1
        return deleted

    def keys(self, pattern):
        return [k for k in self.store.keys() if fnmatch.fnmatch(k, pattern)]

    def incrby(self, key, amount):
        value = int(self.store.get(key, 0)) + amount
        self.store[key] = value
        return value

    def expire(self, key, ttl):
        self.ttls[key] = ttl
        return True

    def ttl(self, key):
        return self.ttls.get(key, -1)

    def exists(self, key):
        return 1 if key in self.store else 0

    def info(self, section):
        return {"total_commands_processed": 1, "keyspace_hits": 1, "keyspace_misses": 0}


@pytest.mark.unit
def test_cache_manager_basic_ops():
    manager = CacheManager(redis_url="redis://localhost:6379/0")
    manager._client = FakeRedis()
    manager.enabled = True

    assert manager.set("ns", "key1", {"a": 1}, ttl=60) is True
    assert manager.get("ns", "key1") == {"a": 1}
    assert manager.exists("ns", "key1") is True

    ttl = manager.get_ttl("ns", "key1")
    assert ttl == 60

    new_val = manager.increment("ns", "counter", amount=2, ttl=30)
    assert new_val == 2

    assert manager.delete("ns", "key1") is True

    manager.set("ns", "a:1", "x")
    manager.set("ns", "a:2", "y")
    deleted = manager.delete_pattern("ns", "a:*")
    assert deleted == 2

    manager.set("ns", "b:1", "z")
    cleared = manager.clear_namespace("ns")
    assert cleared >= 1


@pytest.mark.unit
def test_cached_decorator_and_cache_aside():
    manager = CacheManager(redis_url="redis://localhost:6379/0")
    manager._client = FakeRedis()
    manager.enabled = True

    # Use local cache manager by monkeypatching global instance on module
    import importlib
    cache_module = importlib.import_module("src.cache.cache_manager")
    original_manager = cache_module.cache_manager
    cache_module.cache_manager = manager

    calls = {"count": 0}

    @cached(namespace="demo", ttl=30)
    def compute(x, y):
        calls["count"] += 1
        return x + y

    assert compute(1, 2) == 3
    assert compute(1, 2) == 3
    assert calls["count"] == 1

    compute.cache_invalidate(1, 2)
    assert compute(1, 2) == 3
    assert calls["count"] == 2

    def loader():
        return {"value": 42}

    data = cache_aside(namespace="demo", key="item", loader=loader, ttl=10)
    assert data["value"] == 42
    data_cached = cache_aside(namespace="demo", key="item", loader=lambda: {"value": 99}, ttl=10)
    assert data_cached["value"] == 42

    cache_module.cache_manager = original_manager

import json
import fnmatch
import pytest
from datetime import datetime, timezone

from src.cache.celex_cache import CelexCache


class FakePipeline:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.commands = []

    def setex(self, key, ttl, value):
        self.commands.append((key, ttl, value))

    def execute(self):
        for key, _ttl, value in self.commands:
            self.redis_client.data[key] = value


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.closed = False

    def ping(self):
        return True

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value

    def mget(self, keys):
        return [self.data.get(key) for key in keys]

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.data:
                del self.data[key]
                deleted += 1
        return deleted

    def scan_iter(self, match=None, count=None):
        for key in list(self.data.keys()):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    def info(self):
        return {
            "used_memory": 1024 * 1024,
            "total_commands_processed": 10,
            "keyspace_hits": 3,
            "keyspace_misses": 1,
        }

    def pipeline(self):
        return FakePipeline(self)

    def close(self):
        self.closed = True


@pytest.mark.unit
def test_celex_cache_get_set(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake)

    cache = CelexCache(redis_url="redis://fake")
    metadata = {
        "title": "Doc",
        "date_document": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    assert cache.set("32016R0679", metadata) is True

    got = cache.get("32016R0679")
    assert got["title"] == "Doc"
    assert isinstance(got["date_document"], datetime)

    results = cache.get_many(["32016R0679", "MISSING"])
    assert results["32016R0679"]["title"] == "Doc"
    assert results["MISSING"] is None


@pytest.mark.unit
def test_celex_cache_bulk_and_stats(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("redis.from_url", lambda *args, **kwargs: fake)

    cache = CelexCache(redis_url="redis://fake")
    entries = {
        "32020R0001": {
            "title": "Doc1",
            "date_document": datetime(2024, 1, 1, tzinfo=timezone.utc),
        },
        "32020R0002": {
            "title": "Doc2",
            "date_entry_into_force": datetime(2024, 1, 2, tzinfo=timezone.utc),
        },
    }
    count = cache.set_many(entries)
    assert count == 2

    results = cache.get_many(["32020R0001", "32020R0002"])
    assert results["32020R0001"]["title"] == "Doc1"
    assert isinstance(results["32020R0001"]["date_document"], datetime)

    assert cache.delete("32020R0001") is True
    cleared = cache.clear_all()
    assert cleared >= 0

    stats = cache.get_stats()
    assert stats["connected"] is True
    assert stats["hit_rate"] >= 0
    assert cache.is_connected() is True

    cache.close()
    assert fake.closed is True


@pytest.mark.unit
def test_celex_cache_no_client(monkeypatch):
    import redis

    def raise_conn(*args, **kwargs):
        raise redis.ConnectionError("boom")

    monkeypatch.setattr(redis, "from_url", raise_conn)
    cache = CelexCache(redis_url="redis://bad")

    assert cache.get("X") is None
    assert cache.set("X", {"a": 1}) is False
    assert cache.get_many(["X"]) == {"X": None}
    assert cache.set_many({"X": {"a": 1}}) == 0
    assert cache.delete("X") is False
    assert cache.clear_all() == 0
    assert cache.get_stats()["connected"] is False
    assert cache.is_connected() is False
    cache.close()

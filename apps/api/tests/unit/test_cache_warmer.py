import pytest

from src.cache.cache_warmer import CacheWarmer
import src.cache.cache_warmer as warmer_module
from src.cache.cache_manager import CacheManager


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.raise_info = False

    def ping(self):
        return True

    def info(self, section):
        if self.raise_info:
            raise RuntimeError("boom")
        return {"total_commands_processed": 1, "keyspace_hits": 2, "keyspace_misses": 1}


@pytest.mark.unit
def test_cache_warmer_methods(db_session, monkeypatch):
    warmer = CacheWarmer()

    monkeypatch.setattr(warmer_module, "get_cached_active_rules", lambda db: [1, 2])
    monkeypatch.setattr(warmer_module, "get_cached_sanctions_list", lambda: ["a", "b"])
    monkeypatch.setattr(warmer_module, "get_cached_dashboard_stats", lambda db: {"total_alerts": 1})

    warmer.warm_rules_cache(db_session)
    warmer.warm_sanctions_cache()
    warmer.warm_dashboard_cache(db_session)

    assert "rules" in warmer.warmed_namespaces
    assert "sanctions" in warmer.warmed_namespaces
    assert "dashboard" in warmer.warmed_namespaces

    # Cache stats
    manager = CacheManager(redis_url="redis://localhost:6379/0")
    manager._client = FakeRedis()
    manager.enabled = True
    monkeypatch.setattr(warmer_module, "cache_manager", manager)

    stats = warmer.get_cache_stats()
    assert stats["enabled"] is True


@pytest.mark.unit
def test_cache_warmer_warm_all_and_user_cache(monkeypatch):
    warmer = CacheWarmer()

    class DummyDB:
        def __init__(self):
            self.closed = False
            self.rolled_back = False

        def close(self):
            self.closed = True

        def rollback(self):
            self.rolled_back = True

    dummy_db = DummyDB()

    monkeypatch.setattr(warmer_module, "SessionLocal", lambda: dummy_db)
    monkeypatch.setattr(warmer_module, "get_cached_active_rules", lambda db: [])
    monkeypatch.setattr(warmer_module, "get_cached_sanctions_list", lambda: [])
    monkeypatch.setattr(warmer_module, "get_cached_dashboard_stats", lambda db: {"total_alerts": 0})

    warmer.warm_all()
    assert dummy_db.closed is True
    assert set(["rules", "sanctions", "dashboard"]).issubset(set(warmer.warmed_namespaces))

    import src.cache.cached_queries as cached_queries

    def fake_profile(db, user_id):
        if user_id == "bad":
            raise ValueError("boom")
        return {"user_id": user_id}

    monkeypatch.setattr(cached_queries, "get_cached_user_risk_profile", fake_profile)
    warmer.warm_user_cache(dummy_db, ["ok", "bad"])
    assert "user_risk_profile" in warmer.warmed_namespaces


@pytest.mark.unit
def test_cache_warmer_stats_error(monkeypatch):
    warmer = CacheWarmer()
    manager = CacheManager(redis_url="redis://localhost:6379/0")
    fake = FakeRedis()
    fake.raise_info = True
    manager._client = fake
    manager.enabled = True
    monkeypatch.setattr(warmer_module, "cache_manager", manager)

    stats = warmer.get_cache_stats()
    assert stats["enabled"] is True
    assert "error" in stats

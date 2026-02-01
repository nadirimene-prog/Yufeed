import pytest
from datetime import datetime, timedelta, timezone
import fnmatch

import importlib
from src.cache.cache_manager import CacheManager
import src.cache.cached_queries as cached_queries
from src.models.transaction_models import Transaction, Alert, MonitoringRule


class FakeRedis:
    def __init__(self):
        self.store = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    def keys(self, pattern):
        return [k for k in self.store.keys() if fnmatch.fnmatch(k, pattern)]

    def incrby(self, key, amount):
        value = int(self.store.get(key, 0)) + amount
        self.store[key] = value
        return value

    def expire(self, key, ttl):
        return True

    def ttl(self, key):
        return 10

    def exists(self, key):
        return 1 if key in self.store else 0


@pytest.mark.unit
def test_cached_queries_flow(db_session, monkeypatch):
    # Patch cache manager
    fake_manager = CacheManager(redis_url="redis://localhost:6379/0")
    fake_manager._client = FakeRedis()
    fake_manager.enabled = True

    cache_module = importlib.import_module("src.cache.cache_manager")
    original_manager = cache_module.cache_manager
    cache_module.cache_manager = fake_manager
    cached_queries.cache_manager = fake_manager

    try:
        now = datetime.now(timezone.utc)
        txn = Transaction(
            tenant_id="default",
            transaction_id="txn_cache",
            user_id="user_cache",
            amount=1000,
            currency="USD",
            transaction_type="deposit",
            timestamp=now - timedelta(days=1),
            status="completed",
            country_code="US",
        )
        alert = Alert(
            tenant_id="default",
            alert_id="alert_cache",
            alert_type="velocity",
            severity="high",
            transaction=txn,
            user_id="user_cache",
            status="pending",
            risk_score=80,
        )
        rule = MonitoringRule(
            tenant_id="default",
            rule_id="RULE-CACHE",
            name="Cache Rule",
            description="desc",
            category="velocity",
            severity="high",
            conditions={"conditions": [{"field": "amount", "operator": ">", "value": 100}], "logic": "AND"},
            thresholds=None,
            enabled=True,
        )
        db_session.add_all([txn, alert, rule])
        db_session.commit()

        profile = cached_queries.get_cached_user_risk_profile(db_session, "user_cache")
        assert profile["alert_count"] == 1

        cached_queries.invalidate_user_risk_profile("user_cache")

        rule_data = cached_queries.get_cached_rule(db_session, "RULE-CACHE")
        assert rule_data["rule_id"] == "RULE-CACHE"

        active_rules = cached_queries.get_cached_active_rules(db_session)
        assert active_rules

        cached_queries.invalidate_rules_cache()

        features = cached_queries.get_cached_user_features(db_session, "user_cache")
        assert features["transaction_count_30d"] >= 1

        network = cached_queries.get_cached_transaction_network(db_session, "user_cache", depth=1)
        assert network["center_user"] == "user_cache"

        dashboard = cached_queries.get_cached_dashboard_stats(db_session)
        assert "total_alerts" in dashboard

        cached_queries.cache_search_results("q", {"a": 1}, 1, 10, {"total": 0}, ttl=10)
        cached = cached_queries.get_cached_search_results("q", {"a": 1}, 1, 10)
        assert cached["total"] == 0
    finally:
        cache_module.cache_manager = original_manager
        cached_queries.cache_manager = original_manager

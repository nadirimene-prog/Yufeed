import pytest

from src.api import ai_costs as ai_costs_api


@pytest.mark.unit
def test_usage_summary_injects_tracking_status(monkeypatch):
    monkeypatch.setattr(ai_costs_api, "get_current_tenant", lambda: "tenant_1")

    class DummyService:
        def __init__(self, db):
            self.db = db

        def get_usage_summary(self, tenant_id, start_date, end_date):
            assert tenant_id == "tenant_1"
            return {
                "summary": {
                    "total_calls": 1,
                    "total_cost_usd": 0.01,
                    "total_tokens": 100,
                    "avg_cost_per_call": 0.01,
                },
                "by_provider": [],
                "by_model": [],
                "by_operation": [],
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            }

    monkeypatch.setattr(ai_costs_api, "AICostService", DummyService)

    result = ai_costs_api.get_usage_summary(days=7, db=object())
    assert result["tracking_status"] == "full"

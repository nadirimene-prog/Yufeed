import pytest


class _DummyBudget:
    daily_limit_usd = 5.0
    monthly_limit_usd = 100.0
    warning_threshold_percent = 80
    critical_threshold_percent = 95


class _DummyService:
    def __init__(self, db):
        self.db = db

    def update_budget(self, **kwargs):
        return _DummyBudget()

    def get_usage_summary(self, tenant_id, start_date, end_date):
        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_calls": 1,
                "total_cost_usd": 0.01,
                "total_tokens": 10,
                "avg_cost_per_call": 0.01,
            },
            "by_provider": [],
            "by_model": [],
            "by_operation": [],
        }


@pytest.mark.unit
def test_ai_costs_budget_requires_admin_role(client, auth_headers, monkeypatch):
    import src.api.ai_costs as ai_costs_api

    monkeypatch.setattr(ai_costs_api, "get_current_tenant", lambda: "default")
    monkeypatch.setattr(ai_costs_api, "AICostService", _DummyService)

    response = client.put(
        "/api/ai-costs/budget",
        headers=auth_headers,  # viewer role
        json={"daily_limit_usd": 12.5},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_ai_costs_budget_allows_admin(client, admin_headers, monkeypatch):
    import src.api.ai_costs as ai_costs_api

    monkeypatch.setattr(ai_costs_api, "get_current_tenant", lambda: "default")
    monkeypatch.setattr(ai_costs_api, "AICostService", _DummyService)

    response = client.put(
        "/api/ai-costs/budget",
        headers=admin_headers,
        json={"daily_limit_usd": 12.5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Budget updated successfully"
    assert payload["budget"]["daily_limit_usd"] == _DummyBudget.daily_limit_usd


@pytest.mark.unit
def test_ai_costs_usage_summary_returns_tracking_status(client, admin_headers, monkeypatch):
    import src.api.ai_costs as ai_costs_api

    monkeypatch.setattr(ai_costs_api, "get_current_tenant", lambda: "default")
    monkeypatch.setattr(ai_costs_api, "AICostService", _DummyService)

    response = client.get("/api/ai-costs/usage-summary", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["tracking_status"] == "full"

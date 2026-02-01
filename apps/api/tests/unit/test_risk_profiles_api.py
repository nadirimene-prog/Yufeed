import pytest
from datetime import datetime, timezone
from decimal import Decimal

from src.models.transaction_models import UserRiskProfile, Alert
from src.services.risk_scoring import RiskScoringService


@pytest.mark.unit
class TestRiskProfilesAPI:
    def test_list_get_and_stats(self, client, db_session):
        profile_high = UserRiskProfile(
            tenant_id="default",
            user_id="user_high",
            overall_risk_score=Decimal("85"),
            risk_level="high",
            total_alerts=3,
            critical_alerts=1,
        )
        profile_low = UserRiskProfile(
            tenant_id="default",
            user_id="user_low",
            overall_risk_score=Decimal("10"),
            risk_level="low",
        )
        db_session.add_all([profile_high, profile_low])
        db_session.commit()

        resp = client.get("/api/risk-profiles", params={"risk_level": "high"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["user_id"] == "user_high"

        resp = client.get("/api/risk-profiles/user_high")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "user_high"

        resp = client.get("/api/risk-profiles/statistics/overview")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_profiles"] >= 2
        assert "profiles_by_risk_level" in stats

    def test_activity_summary_and_high_risk_list(self, client, db_session):
        profile = UserRiskProfile(
            tenant_id="default",
            user_id="user_activity",
            overall_risk_score=Decimal("90"),
            risk_level="critical",
        )
        db_session.add(profile)

        db_session.add(
            Alert(
                tenant_id="default",
                alert_id="alert_act_1",
                alert_type="velocity",
                severity="critical",
                user_id="user_activity",
                status="pending",
            )
        )
        db_session.add(
            Alert(
                tenant_id="default",
                alert_id="alert_act_2",
                alert_type="structuring",
                severity="low",
                user_id="user_activity",
                status="pending",
            )
        )
        db_session.commit()

        resp = client.get("/api/risk-profiles/user_activity/activity", params={"days": 30})
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["alert_count"] == 2
        assert summary["critical_alerts"] == 1

        resp = client.get("/api/risk-profiles/high-risk/list")
        assert resp.status_code == 200
        assert any(item["user_id"] == "user_activity" for item in resp.json())

    def test_recalculate_risk_profile(self, client, db_session, monkeypatch):
        profile = UserRiskProfile(
            tenant_id="default",
            user_id="user_recalc",
            overall_risk_score=Decimal("55"),
            risk_level="medium",
        )
        db_session.add(profile)
        db_session.commit()

        def fake_update(self, user_id: str):
            return profile

        monkeypatch.setattr(RiskScoringService, "update_user_risk_profile", fake_update)

        resp = client.post("/api/risk-profiles/user_recalc/recalculate")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "user_recalc"

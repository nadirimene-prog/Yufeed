import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.services.risk_scoring import RiskScoringService
from src.models.transaction_models import Alert, Transaction
from src.tenancy.context import set_current_tenant, clear_current_tenant
from tests.factories import TransactionFactory


@pytest.mark.unit
def test_score_transaction_and_get_risk_level(db_session):
    set_current_tenant("default")
    try:
        tx = TransactionFactory(
            sqlalchemy_session=db_session,
            amount=Decimal("120000"),
            country_code="IR",
            transaction_type="withdrawal",
            user_id="user_risk_1",
            timestamp=datetime.now(timezone.utc),
        )
        db_session.commit()

        service = RiskScoringService(db_session)
        score = service.score_transaction(tx.id)

        assert score >= Decimal("0")
        assert score <= Decimal("100")
        assert service.get_risk_level(Decimal("85")) == "critical"
        assert service.get_risk_level(Decimal("65")) == "high"
        assert service.get_risk_level(Decimal("40")) == "medium"
        assert service.get_risk_level(Decimal("5")) == "low"
    finally:
        clear_current_tenant()


@pytest.mark.unit
def test_update_user_risk_profile_builds_factors(db_session):
    set_current_tenant("default")
    try:
        user_id = "user_risk_profile"
        now = datetime.now(timezone.utc)

        for _ in range(6):
            TransactionFactory(
                sqlalchemy_session=db_session,
                user_id=user_id,
                amount=Decimal("20000"),
                country_code="IR",
                transaction_type="transfer",
                timestamp=now - timedelta(days=1),
            )

        db_session.add(
            Alert(
                tenant_id="default",
                alert_id="alert_critical_1",
                alert_type="velocity",
                severity="critical",
                user_id=user_id,
                status="resolved",
            )
        )
        db_session.add(
            Alert(
                tenant_id="default",
                alert_id="alert_medium_1",
                alert_type="structuring",
                severity="medium",
                user_id=user_id,
                status="pending",
            )
        )
        db_session.commit()

        service = RiskScoringService(db_session)
        profile = service.update_user_risk_profile(user_id)

        assert profile.user_id == user_id
        assert profile.total_alerts == 2
        assert profile.critical_alerts == 1
        assert profile.primary_country == "IR"
        assert "high_volume" in (profile.risk_factors or {})
        assert "high_risk_countries" in (profile.risk_factors or {})
        assert "critical_alerts" in (profile.risk_factors or {})
    finally:
        clear_current_tenant()

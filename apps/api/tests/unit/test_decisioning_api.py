import pytest
from types import SimpleNamespace
from datetime import datetime, timezone

from src.api import decisioning as decisioning_api
from src.auth.dependencies import CurrentUser
from src.models.transaction_models import Transaction


@pytest.mark.unit
def test_decisioning_ingest_and_decide(db_session, monkeypatch):
    # Stub risk scoring + rules engine
    class DummyRiskScoringService:
        def __init__(self, db):
            self.db = db

        def score_transaction(self, transaction_id):
            return 42

        def get_risk_level(self, score):
            return "medium"

        def update_user_risk_profile(self, user_id):
            return None

    class DummyRulesEngine:
        def __init__(self, db):
            self.db = db

        def evaluate_transaction(self, transaction_id):
            return [SimpleNamespace(alert_id="ALT-1", rule_id="RULE-1")]

    monkeypatch.setattr(decisioning_api, "RiskScoringService", DummyRiskScoringService)
    monkeypatch.setattr(decisioning_api, "RulesEngine", DummyRulesEngine)

    txn = Transaction(
        tenant_id="default",
        transaction_id="txn_decide_1",
        user_id="user_1",
        amount=1000.0,
        currency="USD",
        transaction_type="deposit",
        timestamp=datetime.now(timezone.utc),
        status="completed",
        country_code="US",
    )
    db_session.add(txn)
    db_session.commit()

    current_user = CurrentUser("user-1", "user@example.com", "admin", tenant_id="default")

    ingest = decisioning_api.ingest_event(
        decisioning_api.EventIngestRequest(
            event_type="txn_fiat",
            payload={"transaction_id": txn.transaction_id},
            entity_type="transaction",
            entity_id=txn.transaction_id,
            source="tests",
        ),
        db_session,
        current_user,
    )
    assert ingest.event_id

    decision = decisioning_api.decide(
        decisioning_api.DecisionRequest(
            event_id=ingest.event_id,
            event_type="txn_fiat",
            transaction_id=txn.id,
            payload={"user_id": txn.user_id},
            entity_type="transaction",
            entity_id=txn.transaction_id,
            source="tests",
        ),
        db_session,
        current_user,
    )
    assert decision.decision in {"approve", "review"}
    assert decision.alerts

    fetched = decisioning_api.get_decision(decision.decision_id, db_session, current_user)
    assert fetched.decision_id == decision.decision_id

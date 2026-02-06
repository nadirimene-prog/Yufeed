from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from sqlalchemy.orm import sessionmaker

from src.models.transaction_models import Transaction, MonitoringRule, Alert, UserRiskProfile
from src.tasks import transaction_processing


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.integration
def test_process_transaction_task_is_tenant_scoped(db_session, test_db_engine, monkeypatch):
    # Patch Celery task SessionLocal to use the test DB engine.
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    monkeypatch.setattr(transaction_processing, "SessionLocal", TestSessionLocal)

    user_id = f"shared-user-{uuid.uuid4().hex[:8]}"

    # Tenant B has many transactions (should NOT affect tenant A scoring)
    for i in range(10):
        db_session.add(
            Transaction(
                tenant_id="tenant-b",
                transaction_id=f"proc-b-{uuid.uuid4().hex[:10]}-{i}",
                user_id=user_id,
                amount=10,
                currency="USD",
                transaction_type=None,
                timestamp=utc_now() - timedelta(minutes=30 + i),
                status="completed",
            )
        )

    # Tenant B has a rule that would trigger on any positive amount (should NOT run for tenant A)
    db_session.add(
        MonitoringRule(
            tenant_id="tenant-b",
            rule_id="RULE-TENANT-B-ALWAYS",
            name="Always trigger",
            description="Should never evaluate cross-tenant",
            category="amount_threshold",
            severity="high",
            priority=3,
            conditions={
                "logic": "AND",
                "conditions": [{"field": "amount", "operator": "greater_than", "value": 0}],
            },
            thresholds=None,
            enabled=True,
            version=1,
        )
    )

    # Tenant A transaction to process
    tx_a = Transaction(
        tenant_id="tenant-a",
        transaction_id=f"proc-a-{uuid.uuid4().hex[:10]}",
        user_id=user_id,
        amount=10,
        currency="USD",
        transaction_type=None,
        timestamp=utc_now() - timedelta(minutes=5),
        status="completed",
    )
    db_session.add(tx_a)
    db_session.commit()

    result = transaction_processing.process_transaction_task(tx_a.id, "tenant-a")
    assert result["status"] == "success"

    db_session.expire_all()

    # Risk score should not include velocity points from tenant-b activity.
    refreshed_tx_a = (
        db_session.query(Transaction)
        .filter(Transaction.id == tx_a.id, Transaction.tenant_id == "tenant-a")
        .first()
    )
    assert refreshed_tx_a is not None
    assert refreshed_tx_a.risk_score == Decimal("5")

    # No alerts should be created for tenant-a (since only tenant-b has a rule).
    assert db_session.query(Alert).filter(Alert.tenant_id == "tenant-a").count() == 0

    # User risk profile stats should be tenant-scoped (only the tenant-a transaction counted).
    profile = (
        db_session.query(UserRiskProfile)
        .filter(UserRiskProfile.tenant_id == "tenant-a", UserRiskProfile.user_id == user_id)
        .first()
    )
    assert profile is not None
    assert profile.transaction_velocity_30d == 1

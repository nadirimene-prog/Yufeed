import pytest
from datetime import datetime, timedelta, timezone

from src.api import network_analysis as network_api
from src.models.transaction_models import Transaction, UserRiskProfile


@pytest.mark.unit
def test_network_analysis_endpoints(db_session):
    now = datetime.now(timezone.utc)

    profiles = [
        UserRiskProfile(tenant_id="default", user_id="user_a", risk_level="high"),
        UserRiskProfile(tenant_id="default", user_id="user_b", risk_level="high"),
        UserRiskProfile(tenant_id="default", user_id="user_c", risk_level="medium"),
        UserRiskProfile(tenant_id="default", user_id="user_d", risk_level="low"),
    ]
    db_session.add_all(profiles)

    txs = [
        Transaction(
            tenant_id="default",
            transaction_id="tx_ab",
            user_id="user_a",
            counterparty_id="user_b",
            amount=50000,
            currency="USD",
            transaction_type="transfer",
            timestamp=now - timedelta(days=1),
            status="completed",
            ip_address="1.1.1.1",
            device_fingerprint="dev1",
        ),
        Transaction(
            tenant_id="default",
            transaction_id="tx_bc",
            user_id="user_b",
            counterparty_id="user_c",
            amount=60000,
            currency="USD",
            transaction_type="transfer",
            timestamp=now - timedelta(days=1),
            status="completed",
            ip_address="1.1.1.1",
            device_fingerprint="dev1",
        ),
        Transaction(
            tenant_id="default",
            transaction_id="tx_ca",
            user_id="user_c",
            counterparty_id="user_a",
            amount=70000,
            currency="USD",
            transaction_type="transfer",
            timestamp=now - timedelta(days=1),
            status="completed",
            ip_address="1.1.1.1",
            device_fingerprint="dev1",
        ),
        Transaction(
            tenant_id="default",
            transaction_id="tx_ad",
            user_id="user_a",
            counterparty_id="user_d",
            amount=20000,
            currency="USD",
            transaction_type="transfer",
            timestamp=now - timedelta(days=2),
            status="completed",
            ip_address="2.2.2.2",
            device_fingerprint="dev2",
        ),
        Transaction(
            tenant_id="default",
            transaction_id="tx_da",
            user_id="user_d",
            counterparty_id="user_a",
            amount=20000,
            currency="USD",
            transaction_type="transfer",
            timestamp=now - timedelta(days=2),
            status="completed",
            ip_address="2.2.2.2",
            device_fingerprint="dev2",
        ),
    ]
    db_session.add_all(txs)
    db_session.commit()

    analysis = network_api.analyze_user_network("user_a", depth=2, days=90, db=db_session)
    assert analysis["network_size"] >= 3

    related = network_api.find_related_users("user_a", relationship_type="all", db=db_session)
    assert related["count"] >= 1

    rings = network_api.detect_fraud_rings(
        min_cluster_size=2,
        min_suspicion_score=10.0,
        days=90,
        limit=5,
        db=db_session,
    )
    assert "rings" in rings

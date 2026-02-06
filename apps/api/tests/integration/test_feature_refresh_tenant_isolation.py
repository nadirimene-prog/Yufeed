from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import sessionmaker
import uuid

from src.models.transaction_models import Transaction, FeatureValue
from src.tasks import feature_refresh


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.integration
def test_refresh_user_features_is_tenant_scoped(db_session, test_db_engine, monkeypatch):
    # Patch Celery task SessionLocal to use the test DB engine.
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    monkeypatch.setattr(feature_refresh, "SessionLocal", TestSessionLocal)

    user_id = f"shared-user-{uuid.uuid4().hex[:8]}"

    # Tenant A: 1 txn
    db_session.add(
        Transaction(
            tenant_id="tenant-a",
            transaction_id=f"feat-a-{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            amount=10,
            currency="USD",
            transaction_type="payment",
            timestamp=utc_now() - timedelta(minutes=5),
            status="completed",
        )
    )

    # Tenant B: 3 txns for the same user_id
    for i in range(3):
        db_session.add(
            Transaction(
                tenant_id="tenant-b",
                transaction_id=f"feat-b-{uuid.uuid4().hex[:10]}-{i}",
                user_id=user_id,
                amount=10,
                currency="USD",
                transaction_type="payment",
                timestamp=utc_now() - timedelta(minutes=10 + i),
                status="completed",
            )
        )

    db_session.commit()

    result = feature_refresh.refresh_user_features("tenant-a", user_id, version=1)
    assert result["status"] == "success"

    db_session.expire_all()

    # Features should only be written for tenant-a.
    tenant_a_features = (
        db_session.query(FeatureValue)
        .filter(
            FeatureValue.tenant_id == "tenant-a",
            FeatureValue.entity_type == "user",
            FeatureValue.entity_id == user_id,
        )
        .all()
    )
    assert tenant_a_features

    tenant_b_features = (
        db_session.query(FeatureValue)
        .filter(
            FeatureValue.tenant_id == "tenant-b",
            FeatureValue.entity_type == "user",
            FeatureValue.entity_id == user_id,
        )
        .all()
    )
    assert tenant_b_features == []

    # Sanity: a count-based feature should reflect tenant-a data only (1 txn).
    count_feature = (
        db_session.query(FeatureValue)
        .filter(
            FeatureValue.tenant_id == "tenant-a",
            FeatureValue.entity_type == "user",
            FeatureValue.entity_id == user_id,
            FeatureValue.feature_name == "velocity_24h_count",
            FeatureValue.version == 1,
        )
        .first()
    )
    assert count_feature is not None
    assert count_feature.feature_value == 1

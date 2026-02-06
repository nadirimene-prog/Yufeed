import pytest
from datetime import datetime, timedelta, timezone

from src.services.time_series_features import TimeSeriesFeatureExtractor
from src.models.transaction_models import Transaction


@pytest.mark.unit
def test_time_series_features_with_data(db_session):
    now = datetime.utcnow()
    user_id = "user_ts"

    txs = []
    for days_ago in range(1, 6):
        txs.append(
            Transaction(
                tenant_id="default",
                transaction_id=f"txn_ts_{days_ago}",
                user_id=user_id,
                amount=100 * days_ago,
                currency="USD",
                transaction_type="deposit",
            timestamp=now - timedelta(days=days_ago),
                status="completed",
                country_code="US",
            )
        )
    db_session.add_all(txs)
    db_session.commit()

    extractor = TimeSeriesFeatureExtractor(db_session)
    features = extractor.extract_features(
        tenant_id="default",
        user_id=user_id,
        current_time=now,
        lookback_days=30,
    )

    assert "velocity_24h_count" in features
    assert "amount_ema_7d" in features
    assert "amount_zscore_last" in features
    assert "velocity_acceleration" in features


@pytest.mark.unit
def test_time_series_features_no_data(db_session):
    extractor = TimeSeriesFeatureExtractor(db_session)
    features = extractor.extract_features(
        tenant_id="default",
        user_id="missing_user",
        current_time=datetime.utcnow(),
        lookback_days=30,
    )
    assert features["velocity_1h_count"] == 0
    assert features["amount_ema_ratio"] == 1.0

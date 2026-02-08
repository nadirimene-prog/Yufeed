from datetime import datetime, timezone

import pytest

from src.models.transaction_models import FeatureValue
from src.services.feature_store import FeatureStoreService
from src.tenancy.context import TenantContext


def utc_now():
    return datetime.now(timezone.utc)


@pytest.mark.unit
def test_feature_store_service_upsert_and_get(db_session):
    service = FeatureStoreService(db_session)

    with TenantContext("tenant-a"):
        service.upsert_features(
            "user",
            "user-1",
            {
                "velocity_24h": {
                    "value": 3,
                    "feature_type": "numeric",
                    "calculated_at": utc_now(),
                    "version": 1,
                }
            },
        )
        db_session.commit()

        feature = service.get_feature("user", "user-1", "velocity_24h")
        assert feature is not None
        assert feature["value"] == 3
        assert feature["feature_type"] == "numeric"
        assert feature["version"] == 1


@pytest.mark.unit
def test_feature_store_service_upsert_is_idempotent(db_session):
    service = FeatureStoreService(db_session)

    with TenantContext("tenant-a"):
        service.upsert_features(
            "user",
            "user-1",
            {
                "velocity_24h": {
                    "value": 1,
                    "feature_type": "numeric",
                    "calculated_at": utc_now(),
                    "version": 1,
                }
            },
        )
        db_session.commit()

        service.upsert_features(
            "user",
            "user-1",
            {
                "velocity_24h": {
                    "value": 2,
                    "feature_type": "numeric",
                    "calculated_at": utc_now(),
                    "version": 1,
                }
            },
        )
        db_session.commit()

        rows = (
            db_session.query(FeatureValue)
            .filter(
                FeatureValue.tenant_id == "tenant-a",
                FeatureValue.entity_type == "user",
                FeatureValue.entity_id == "user-1",
                FeatureValue.feature_name == "velocity_24h",
                FeatureValue.version == 1,
            )
            .all()
        )
        assert len(rows) == 1
        assert rows[0].feature_value == 2

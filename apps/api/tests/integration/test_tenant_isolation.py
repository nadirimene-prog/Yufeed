"""
Integration tests for tenant isolation across all workflows.

Tests verify that:
- Feature refresh only accesses tenant-scoped data
- Transaction processing only evaluates tenant-scoped rules
- Risk scoring only considers tenant-scoped transaction history
- User profiles are tenant-isolated
- Alerts, cases, and decisions are tenant-isolated

Test Coverage:
- Cross-tenant data leakage prevention
- Tenant-scoped feature computation
- Tenant-scoped rule evaluation
- Tenant-scoped risk scoring
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import secrets
import uuid

import pytest
from sqlalchemy.orm import sessionmaker

from src.models.transaction_models import (
    Transaction,
    MonitoringRule,
    Alert,
    UserRiskProfile,
    FeatureValue,
)
from src.tasks import feature_refresh, transaction_processing


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.integration
class TestFeatureRefreshTenantIsolation:
    """Test feature refresh respects tenant boundaries."""

    def test_refresh_user_features_is_tenant_scoped(self, db_session, test_db_engine, monkeypatch):
        """
        Verify feature refresh only computes features from tenant-scoped transactions.

        Scenario:
        - User exists in both tenant-a and tenant-b
        - Tenant-a: 1 transaction
        - Tenant-b: 3 transactions
        - Refresh features for tenant-a
        - Verify tenant-a features reflect only 1 transaction (not 4)
        """
        # Patch Celery task SessionLocal to use the test DB engine
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        monkeypatch.setattr(feature_refresh, "SessionLocal", TestSessionLocal)

        user_id = f"shared-user-{uuid.uuid4().hex[:8]}"

        # Tenant A: 1 transaction
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

        # Tenant B: 3 transactions for the same user_id
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

        # Refresh features for tenant-a
        result = feature_refresh.refresh_user_features("tenant-a", user_id, version=1)
        assert result["status"] == "success"

        db_session.expire_all()

        # Features should only be written for tenant-a
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

        # Tenant-b should have NO features created (isolation)
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

        # Verify velocity count reflects only tenant-a data (1 transaction, not 4)
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
        assert count_feature.feature_value == 1  # NOT 4


@pytest.mark.integration
class TestTransactionProcessingTenantIsolation:
    """Test transaction processing respects tenant boundaries."""

    def test_process_transaction_task_is_tenant_scoped(
        self, db_session, test_db_engine, monkeypatch
    ):
        """
        Verify transaction processing only evaluates tenant-scoped rules and data.

        Scenario:
        - User exists in both tenant-a and tenant-b
        - Tenant-b: 10 transactions + rule that triggers on amount > 0
        - Tenant-a: 1 transaction, no rules
        - Process tenant-a transaction
        - Verify:
          - Risk score does NOT include tenant-b velocity
          - No alerts created (tenant-b rule should not evaluate)
          - User profile stats only reflect tenant-a data
        """
        # Patch Celery task SessionLocal to use the test DB engine
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        monkeypatch.setattr(transaction_processing, "SessionLocal", TestSessionLocal)

        user_id = f"shared-user-{uuid.uuid4().hex[:8]}"

        # Tenant B: Many transactions (should NOT affect tenant A scoring)
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

        # Tenant B: Rule that would trigger on any positive amount (should NOT run for tenant A)
        db_session.add(
            MonitoringRule(
                tenant_id="tenant-b",
                rule_id=f"RULE-TENANT-B-ALWAYS-{secrets.token_hex(4)}",
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

        # Tenant A: Transaction to process
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

        # Process tenant-a transaction
        result = transaction_processing.process_transaction_task(tx_a.id, "tenant-a")
        assert result["status"] == "success"

        db_session.expire_all()

        # Risk score should NOT include velocity points from tenant-b activity
        refreshed_tx_a = (
            db_session.query(Transaction)
            .filter(Transaction.id == tx_a.id, Transaction.tenant_id == "tenant-a")
            .first()
        )
        assert refreshed_tx_a is not None
        assert refreshed_tx_a.risk_score == Decimal(
            "5"
        )  # Base score, not elevated by tenant-b velocity

        # No alerts should be created for tenant-a (tenant-b rule should not trigger)
        tenant_a_alerts = db_session.query(Alert).filter(Alert.tenant_id == "tenant-a").count()
        assert (
            tenant_a_alerts == 0
        ), "Tenant-b rule triggered for tenant-a transaction - ISOLATION BREACH"

        # User risk profile should only reflect tenant-a data (1 transaction, not 11)
        profile = (
            db_session.query(UserRiskProfile)
            .filter(UserRiskProfile.tenant_id == "tenant-a", UserRiskProfile.user_id == user_id)
            .first()
        )
        assert profile is not None
        assert profile.transaction_velocity_30d == 1  # NOT 11


@pytest.mark.integration
class TestAPIEndpointTenantIsolation:
    """Test API endpoints respect tenant boundaries."""

    def test_alerts_endpoint_tenant_isolation(
        self, client, auth_headers, db_session, tenant_factory
    ):
        """
        Verify alerts API endpoint only returns tenant-scoped alerts.

        Scenario:
        - Create alerts for tenant-a and tenant-b
        - Query alerts with tenant-a context
        - Verify only tenant-a alerts returned
        """
        from tests.factories import TenantFactory

        # Create two tenants
        tenant1 = TenantFactory(tenant_id="tenant_alert_api_1", sqlalchemy_session=db_session)
        tenant2 = TenantFactory(tenant_id="tenant_alert_api_2", sqlalchemy_session=db_session)
        db_session.commit()

        # Create alert for tenant1
        alert1_response = client.post(
            "/api/alerts",
            headers={**auth_headers, "X-Tenant-ID": "tenant_alert_api_1"},
            json={
                "alert_type": "api_isolation_test",
                "severity": "high",
                "user_id": "shared_user_api",
                "description": "Tenant 1 alert",
                "risk_score": 70.0,
            },
        )
        assert alert1_response.status_code == 201
        alert1_id = alert1_response.json()["alert_id"]

        # Create alert for tenant2
        alert2_response = client.post(
            "/api/alerts",
            headers={**auth_headers, "X-Tenant-ID": "tenant_alert_api_2"},
            json={
                "alert_type": "api_isolation_test",
                "severity": "medium",
                "user_id": "shared_user_api",
                "description": "Tenant 2 alert",
                "risk_score": 50.0,
            },
        )
        assert alert2_response.status_code == 201
        alert2_id = alert2_response.json()["alert_id"]

        # Query alerts for tenant1
        tenant1_alerts = client.get(
            "/api/alerts", headers={**auth_headers, "X-Tenant-ID": "tenant_alert_api_1"}
        )
        tenant1_alert_ids = [a["alert_id"] for a in tenant1_alerts.json()]

        assert alert1_id in tenant1_alert_ids
        assert (
            alert2_id not in tenant1_alert_ids
        ), "Tenant 1 can see Tenant 2's alert via API - ISOLATION BREACH"

        # Query alerts for tenant2
        tenant2_alerts = client.get(
            "/api/alerts", headers={**auth_headers, "X-Tenant-ID": "tenant_alert_api_2"}
        )
        tenant2_alert_ids = [a["alert_id"] for a in tenant2_alerts.json()]

        assert alert2_id in tenant2_alert_ids
        assert (
            alert1_id not in tenant2_alert_ids
        ), "Tenant 2 can see Tenant 1's alert via API - ISOLATION BREACH"

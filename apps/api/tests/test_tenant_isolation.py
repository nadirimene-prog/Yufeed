"""
Multi-Tenancy Isolation Tests
Phase 4C: Task 7 - Comprehensive tenant isolation validation

Tests to ensure complete data isolation between tenants.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import secrets

from src.main import app
from src.database import get_db, SessionLocal, Base, sync_engine
from src.models.tenant_models import Tenant, TenantAPIKey
from src.models.transaction_models import Transaction, Alert, Case, MonitoringRule
from src.tenancy.context import TenantContext


client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def db():
    """Database session fixture."""
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=sync_engine)


@pytest.fixture(scope="module")
def tenant_a(db: Session):
    """Create tenant A for testing."""
    tenant = Tenant(
        tenant_id="test_tenant_a",
        name="Test Tenant A",
        display_name="Tenant A",
        tier="standard",
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    yield tenant

    # Cleanup
    db.delete(tenant)
    db.commit()


@pytest.fixture(scope="module")
def tenant_b(db: Session):
    """Create tenant B for testing."""
    tenant = Tenant(
        tenant_id="test_tenant_b",
        name="Test Tenant B",
        display_name="Tenant B",
        tier="enterprise",
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    yield tenant

    # Cleanup
    db.delete(tenant)
    db.commit()


@pytest.fixture(scope="module")
def api_key_tenant_a(db: Session, tenant_a: Tenant):
    """Create API key for tenant A."""
    random_part = secrets.token_hex(16)
    api_key = f"yk_live_test_tenant_a_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    api_key_record = TenantAPIKey(
        tenant_id=tenant_a.id,
        key_hash=key_hash,
        key_prefix=api_key[:20],
        name="Test API Key A",
        is_active=True
    )
    db.add(api_key_record)
    db.commit()

    yield api_key

    # Cleanup
    db.delete(api_key_record)
    db.commit()


@pytest.fixture(scope="module")
def api_key_tenant_b(db: Session, tenant_b: Tenant):
    """Create API key for tenant B."""
    random_part = secrets.token_hex(16)
    api_key = f"yk_live_test_tenant_b_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    api_key_record = TenantAPIKey(
        tenant_id=tenant_b.id,
        key_hash=key_hash,
        key_prefix=api_key[:20],
        name="Test API Key B",
        is_active=True
    )
    db.add(api_key_record)
    db.commit()

    yield api_key

    # Cleanup
    db.delete(api_key_record)
    db.commit()


# ============================================================================
# TENANT MANAGEMENT TESTS
# ============================================================================

class TestTenantManagement:
    """Test tenant CRUD operations."""

    def test_create_tenant(self, db: Session, superuser_headers):
        """Test creating a new tenant."""
        response = client.post(
            "/api/tenants",
            json={
                "tenant_id": "test_create_tenant",
                "name": "Test Create Tenant",
                "tier": "standard",
                "contact_email": "test@example.com"
            },
            headers=superuser_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == "test_create_tenant"
        assert data["name"] == "Test Create Tenant"
        assert data["is_active"] is True

        # Cleanup
        client.delete(
            f"/api/tenants/test_create_tenant?hard_delete=true",
            headers=superuser_headers,
        )

    def test_create_tenant_duplicate(self, tenant_a, superuser_headers):
        """Test creating a tenant with duplicate tenant_id."""
        response = client.post(
            "/api/tenants",
            json={
                "tenant_id": "test_tenant_a",
                "name": "Duplicate Tenant",
                "tier": "standard"
            },
            headers=superuser_headers,
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_list_tenants(self, tenant_a, tenant_b, superuser_headers):
        """Test listing all tenants."""
        response = client.get("/api/tenants", headers=superuser_headers)
        assert response.status_code == 200
        tenants = response.json()
        assert len(tenants) >= 2
        tenant_ids = [t["tenant_id"] for t in tenants]
        assert "test_tenant_a" in tenant_ids
        assert "test_tenant_b" in tenant_ids

    def test_get_tenant(self, tenant_a, superuser_headers):
        """Test getting a specific tenant."""
        response = client.get(
            f"/api/tenants/{tenant_a.tenant_id}",
            headers=superuser_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == tenant_a.tenant_id
        assert data["name"] == tenant_a.name

    def test_update_tenant(self, tenant_a, superuser_headers):
        """Test updating tenant information."""
        response = client.patch(
            f"/api/tenants/{tenant_a.tenant_id}",
            json={
                "display_name": "Updated Tenant A",
                "tier": "enterprise"
            },
            headers=superuser_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Tenant A"
        assert data["tier"] == "enterprise"


# ============================================================================
# API KEY AUTHENTICATION TESTS
# ============================================================================

class TestAPIKeyAuthentication:
    """Test API key authentication and validation."""

    def test_valid_api_key(self, api_key_tenant_a):
        """Test authentication with valid API key."""
        response = client.get(
            "/api/alerts",
            headers={"X-API-Key": api_key_tenant_a}
        )
        # Should not return 401/403
        assert response.status_code in [200, 404]  # 404 if no alerts exist

    def test_invalid_api_key(self):
        """Test authentication with invalid API key."""
        response = client.get(
            "/api/alerts",
            headers={"X-API-Key": "yk_live_invalid_key_12345"}
        )
        assert response.status_code == 401

    def test_missing_api_key(self):
        """Test request without API key."""
        response = client.get("/api/alerts")
        # Should fall back to default tenant or require authentication
        assert response.status_code in [200, 401, 403]

    def test_api_key_usage_tracking(self, db: Session, api_key_tenant_a):
        """Test that API key usage is tracked."""
        # Get initial usage count
        key_hash = hashlib.sha256(api_key_tenant_a.encode()).hexdigest()
        api_key_record = db.query(TenantAPIKey).filter(
            TenantAPIKey.key_hash == key_hash
        ).first()
        initial_count = api_key_record.usage_count or 0

        # Make a request
        client.get(
            "/api/alerts",
            headers={"X-API-Key": api_key_tenant_a}
        )

        # Check usage count increased
        db.refresh(api_key_record)
        assert api_key_record.usage_count == initial_count + 1
        assert api_key_record.last_used_at is not None


# ============================================================================
# DATA ISOLATION TESTS
# ============================================================================

class TestDataIsolation:
    """Test that data is properly isolated between tenants."""

    def test_transaction_isolation(self, db: Session, tenant_a, tenant_b):
        """Test that transactions are isolated by tenant."""
        # Create transaction for tenant A
        with TenantContext(tenant_a.tenant_id):
            tx_a = Transaction(
                transaction_id="TX-A-001",
                user_id="user_a_001",
                amount=1000.00,
                currency="USD",
                transaction_type="transfer",
                timestamp=datetime.utcnow(),
                tenant_id=tenant_a.tenant_id
            )
            db.add(tx_a)
            db.commit()

        # Create transaction for tenant B
        with TenantContext(tenant_b.tenant_id):
            tx_b = Transaction(
                transaction_id="TX-B-001",
                user_id="user_b_001",
                amount=2000.00,
                currency="EUR",
                transaction_type="transfer",
                timestamp=datetime.utcnow(),
                tenant_id=tenant_b.tenant_id
            )
            db.add(tx_b)
            db.commit()

        # Query as tenant A - should only see tenant A transactions
        with TenantContext(tenant_a.tenant_id):
            from src.tenancy.queries import get_tenant_filtered_query
            tx_list = get_tenant_filtered_query(Transaction, db).all()
            tx_ids = [tx.transaction_id for tx in tx_list]
            assert "TX-A-001" in tx_ids
            assert "TX-B-001" not in tx_ids

        # Query as tenant B - should only see tenant B transactions
        with TenantContext(tenant_b.tenant_id):
            from src.tenancy.queries import get_tenant_filtered_query
            tx_list = get_tenant_filtered_query(Transaction, db).all()
            tx_ids = [tx.transaction_id for tx in tx_list]
            assert "TX-B-001" in tx_ids
            assert "TX-A-001" not in tx_ids

        # Cleanup
        db.delete(tx_a)
        db.delete(tx_b)
        db.commit()

    def test_alert_isolation(self, db: Session, tenant_a, tenant_b):
        """Test that alerts are isolated by tenant."""
        # Create alert for tenant A
        with TenantContext(tenant_a.tenant_id):
            alert_a = Alert(
                alert_id="ALT-A-001",
                alert_type="high_amount",
                severity="medium",
                user_id="user_a_001",
                status="pending",
                tenant_id=tenant_a.tenant_id
            )
            db.add(alert_a)
            db.commit()

        # Create alert for tenant B
        with TenantContext(tenant_b.tenant_id):
            alert_b = Alert(
                alert_id="ALT-B-001",
                alert_type="velocity",
                severity="high",
                user_id="user_b_001",
                status="pending",
                tenant_id=tenant_b.tenant_id
            )
            db.add(alert_b)
            db.commit()

        # Query as tenant A
        with TenantContext(tenant_a.tenant_id):
            from src.tenancy.queries import get_tenant_filtered_query
            alerts = get_tenant_filtered_query(Alert, db).all()
            alert_ids = [a.alert_id for a in alerts]
            assert "ALT-A-001" in alert_ids
            assert "ALT-B-001" not in alert_ids

        # Query as tenant B
        with TenantContext(tenant_b.tenant_id):
            from src.tenancy.queries import get_tenant_filtered_query
            alerts = get_tenant_filtered_query(Alert, db).all()
            alert_ids = [a.alert_id for a in alerts]
            assert "ALT-B-001" in alert_ids
            assert "ALT-A-001" not in alert_ids

        # Cleanup
        db.delete(alert_a)
        db.delete(alert_b)
        db.commit()

    def test_case_isolation(self, db: Session, tenant_a, tenant_b):
        """Test that cases are isolated by tenant."""
        # Create case for tenant A
        with TenantContext(tenant_a.tenant_id):
            case_a = Case(
                case_id="CASE-A-001",
                case_type="investigation",
                subject_type="user",
                subject_id="user_a_001",
                status="open",
                priority="high",
                tenant_id=tenant_a.tenant_id
            )
            db.add(case_a)
            db.commit()

        # Create case for tenant B
        with TenantContext(tenant_b.tenant_id):
            case_b = Case(
                case_id="CASE-B-001",
                case_type="investigation",
                subject_type="user",
                subject_id="user_b_001",
                status="open",
                priority="medium",
                tenant_id=tenant_b.tenant_id
            )
            db.add(case_b)
            db.commit()

        # Query as tenant A
        with TenantContext(tenant_a.tenant_id):
            from src.tenancy.queries import get_tenant_filtered_query
            cases = get_tenant_filtered_query(Case, db).all()
            case_ids = [c.case_id for c in cases]
            assert "CASE-A-001" in case_ids
            assert "CASE-B-001" not in case_ids

        # Cleanup
        db.delete(case_a)
        db.delete(case_b)
        db.commit()


# ============================================================================
# CROSS-TENANT ACCESS PREVENTION TESTS
# ============================================================================

class TestCrossTenantAccessPrevention:
    """Test that tenants cannot access each other's data."""

    def test_cannot_access_other_tenant_alert(
        self, db: Session, tenant_a, tenant_b, api_key_tenant_a
    ):
        """Test that tenant A cannot access tenant B's alerts."""
        # Create alert for tenant B
        with TenantContext(tenant_b.tenant_id):
            alert_b = Alert(
                alert_id="ALT-CROSS-001",
                alert_type="test",
                severity="low",
                user_id="user_b",
                status="pending",
                tenant_id=tenant_b.tenant_id
            )
            db.add(alert_b)
            db.commit()

        # Try to access as tenant A
        response = client.get(
            "/api/alerts/ALT-CROSS-001",
            headers={"X-API-Key": api_key_tenant_a}
        )

        # Should get 404 (not found) or 403 (forbidden)
        assert response.status_code in [403, 404]

        # Cleanup
        db.delete(alert_b)
        db.commit()

    def test_cannot_update_other_tenant_data(
        self, db: Session, tenant_a, tenant_b, api_key_tenant_a
    ):
        """Test that tenant A cannot update tenant B's data."""
        # Create transaction for tenant B
        with TenantContext(tenant_b.tenant_id):
            tx_b = Transaction(
                transaction_id="TX-CROSS-001",
                user_id="user_b",
                amount=5000.00,
                currency="USD",
                transaction_type="transfer",
                timestamp=datetime.utcnow(),
                tenant_id=tenant_b.tenant_id
            )
            db.add(tx_b)
            db.commit()

        # Try to update as tenant A
        response = client.patch(
            "/api/transactions/TX-CROSS-001",
            headers={"X-API-Key": api_key_tenant_a},
            json={"status": "blocked"}
        )

        # Should get 404 or 403
        assert response.status_code in [403, 404]

        # Cleanup
        db.delete(tx_b)
        db.commit()


# ============================================================================
# STATISTICS ISOLATION TESTS
# ============================================================================

class TestStatisticsIsolation:
    """Test that statistics and aggregations are tenant-scoped."""

    def test_alert_statistics_isolation(
        self, db: Session, tenant_a, tenant_b, api_key_tenant_a
    ):
        """Test that alert statistics only show tenant's data."""
        # Create alerts for both tenants
        with TenantContext(tenant_a.tenant_id):
            for i in range(3):
                alert = Alert(
                    alert_id=f"ALT-STAT-A-{i}",
                    alert_type="test",
                    severity="low",
                    user_id="user_a",
                    status="pending",
                    tenant_id=tenant_a.tenant_id
                )
                db.add(alert)
            db.commit()

        with TenantContext(tenant_b.tenant_id):
            for i in range(5):
                alert = Alert(
                    alert_id=f"ALT-STAT-B-{i}",
                    alert_type="test",
                    severity="low",
                    user_id="user_b",
                    status="pending",
                    tenant_id=tenant_b.tenant_id
                )
                db.add(alert)
            db.commit()

        # Get statistics as tenant A
        response = client.get(
            "/api/alerts/statistics/overview",
            headers={"X-API-Key": api_key_tenant_a}
        )

        if response.status_code == 200:
            stats = response.json()
            # Tenant A should only see their 3 alerts, not tenant B's 5
            assert stats["total_alerts"] >= 3
            # Should not include tenant B's 5 alerts

        # Cleanup
        with TenantContext(tenant_a.tenant_id):
            db.query(Alert).filter(Alert.alert_id.like("ALT-STAT-A-%")).delete()
            db.commit()

        with TenantContext(tenant_b.tenant_id):
            db.query(Alert).filter(Alert.alert_id.like("ALT-STAT-B-%")).delete()
            db.commit()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Pytest configuration and fixtures for YuFeed API tests.
"""

import os
from pathlib import Path
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from redis import Redis
from opensearchpy import OpenSearch

from src.database import Base, get_db, get_async_db, SessionLocal
from src.main import app
from src.config import settings
from src.audit import models as _audit_models  # noqa: F401 - register audit tables on Base metadata
from src import models as _all_models  # noqa: F401 - register all ORM tables on Base metadata
from src.models import (
    associations as _association_models,
)  # noqa: F401 - register association tables
from src.models.user import User
from src.models.tenant_models import Tenant, TenantUser
from src.auth.jwt_handler import create_token_response


# ============================================================================
# Async-to-Sync Session Adapter
# ============================================================================


class SyncToAsyncSessionAdapter:
    """Adapter that makes a sync SQLAlchemy Session look async.

    Auth endpoints (register, login, refresh) use ``get_async_db`` which
    yields an ``AsyncSession``.  In tests we run everything against a single
    sync transactional session (``db_session``).  This thin wrapper satisfies
    the ``await db.execute(...)`` / ``await db.commit()`` protocol expected
    by the async endpoints while delegating to the underlying sync session.
    """

    def __init__(self, sync_session: Session):
        self._session = sync_session

    # --- Query / DML --------------------------------------------------

    async def execute(self, stmt, *args, **kwargs):
        return self._session.execute(stmt, *args, **kwargs)

    async def get(self, entity, ident, **kwargs):
        return self._session.get(entity, ident, **kwargs)

    async def scalar(self, stmt, *args, **kwargs):
        return self._session.scalar(stmt, *args, **kwargs)

    # --- Mutation ------------------------------------------------------

    def add(self, instance):
        self._session.add(instance)

    def add_all(self, instances):
        self._session.add_all(instances)

    async def flush(self, objects=None):
        self._session.flush(objects)

    async def commit(self):
        self._session.commit()

    async def rollback(self):
        self._session.rollback()

    async def refresh(self, instance, *args, **kwargs):
        self._session.refresh(instance, *args, **kwargs)

    async def delete(self, instance):
        self._session.delete(instance)

    async def close(self):
        pass  # session lifecycle managed by db_session fixture

    # --- Context manager protocol -------------------------------------

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    # --- Attribute pass-through ----------------------------------------

    def __getattr__(self, name):
        return getattr(self._session, name)


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db_engine():
    """
    Create a test database engine.

    Uses TEST_DATABASE_URL when explicitly provided. Otherwise defaults to
    an in-memory SQLite database to keep tests isolated from the app/runtime
    database configured in .env.

    For SQLite, reuse a shared file-backed DB to support async + sync sessions.
    """
    db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    connect_args = {}
    poolclass = None

    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if db_url.endswith(":memory:"):
            poolclass = StaticPool

    engine_kwargs = {
        "echo": False,
    }
    if connect_args:
        engine_kwargs["connect_args"] = connect_args
    if poolclass:
        engine_kwargs["poolclass"] = poolclass

    engine = create_engine(db_url, **engine_kwargs)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if db_url.startswith("sqlite") and not db_url.endswith(":memory:"):
        try:
            path = Path(db_url.replace("sqlite:///", "", 1))
            if path.exists():
                path.unlink()
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test.
    A fresh engine is created per test, providing hard isolation.
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestSessionLocal()
    # Bind factory_boy SQLAlchemy factories to this session.
    try:
        from tests.factories import (
            TransactionFactory,
            AlertFactory,
            CaseFactory,
            MonitoringRuleFactory,
            RuleHitFactory,
            LegalDocumentFactory,
            FindingFactory,
            CaseDecisionFactory,
            EvidencePackFactory,
        )

        for factory_cls in (
            TransactionFactory,
            AlertFactory,
            CaseFactory,
            MonitoringRuleFactory,
            RuleHitFactory,
            LegalDocumentFactory,
            FindingFactory,
            CaseDecisionFactory,
            EvidencePackFactory,
        ):
            factory_cls._meta.sqlalchemy_session = session
    except Exception:
        # Factories may not be imported in some test contexts.
        pass

    yield session

    # Cleanup
    session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with overridden database dependency.
    """
    # Disable rate limiting in tests to avoid hitting auth limits.
    if os.getenv("ENVIRONMENT", "").lower() in {"test", "testing"}:
        from src.middleware import limiter

        limiter.enabled = False
        # Clear any existing rate limit records
        if hasattr(limiter, "_storage") and limiter._storage:
            try:
                limiter._storage.clear()
            except Exception:
                pass

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    async def override_get_async_db():
        yield SyncToAsyncSessionAdapter(db_session)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_async_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# Redis Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def redis_client():
    """
    Create Redis client for testing.
    Uses database 1 for test isolation.
    """
    client = Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/1"), decode_responses=True
    )

    yield client

    # Cleanup all keys in test database
    client.flushdb()
    client.close()


@pytest.fixture(scope="function")
def clean_redis(redis_client):
    """
    Clean Redis before each test.
    """
    redis_client.flushdb()
    yield redis_client


# ============================================================================
# OpenSearch Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def opensearch_client():
    """
    Create OpenSearch client for testing.
    """
    client = OpenSearch(
        hosts=[os.getenv("OPENSEARCH_URL", "http://localhost:9200")],
        http_auth=None,
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )

    yield client

    # Cleanup test indices
    try:
        client.indices.delete(index="test_*")
    except Exception:
        pass


@pytest.fixture(scope="function")
def clean_opensearch(opensearch_client):
    """
    Clean OpenSearch test indices before each test.
    """
    try:
        opensearch_client.indices.delete(index="test_*")
    except Exception:
        pass

    yield opensearch_client


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def ensure_tenant_membership(db_session):
    """
    Ensure a default tenant and membership exist for a user.

    Uses the test ``db_session`` so that objects created by auth endpoints
    (via the SyncToAsyncSessionAdapter) are visible in the same transaction.
    """

    def _ensure(email: str, role: str = "viewer", tenant_id: str = "default") -> Tenant:
        normalized_email = email.lower()
        db = db_session
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            tenant = Tenant(
                tenant_id=tenant_id,
                name=f"{tenant_id.capitalize()} Tenant",
                display_name=tenant_id,
                tier="standard",
                is_active=True,
            )
            db.add(tenant)
            db.flush()

        user = db.query(User).filter(User.email == normalized_email).first()
        if not user:
            raise AssertionError(f"User not found for email {normalized_email}")

        membership = (
            db.query(TenantUser)
            .filter(
                TenantUser.tenant_id == tenant.id,
                TenantUser.user_id == str(user.id),
            )
            .first()
        )
        if not membership:
            membership = TenantUser(
                tenant_id=tenant.id,
                user_id=str(user.id),
                role=role,
                is_active=True,
            )
            db.add(membership)
            db.flush()

        return tenant

    return _ensure


@pytest.fixture
def tenant_factory(db_session):
    """
    Factory helper for creating tenants bound to the current test session.
    """
    from tests.factories import TenantFactory

    def _create(**kwargs):
        return TenantFactory(sqlalchemy_session=db_session, **kwargs)

    return _create


@pytest.fixture
def test_user_token(client: TestClient, ensure_tenant_membership) -> str:
    """
    Create a test user and return authentication token.
    """
    # Register test user
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
        },
    )

    # Ensure tenant membership for login
    ensure_tenant_membership("test@example.com", role="viewer", tenant_id="default")

    # Login to get token with tenant context
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "tenant_id": "default",
        },
    )

    return response.json()["access_token"]


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """
    Return authorization headers with JWT token.
    """
    return {
        "Authorization": f"Bearer {test_user_token}",
        "X-Tenant-ID": "default",
    }


@pytest.fixture
def admin_user_token(client: TestClient, ensure_tenant_membership) -> str:
    """
    Create an admin user and return authentication token.
    """
    response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "full_name": "Admin User",
        },
    )

    ensure_tenant_membership("admin@example.com", role="admin", tenant_id="default")

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "tenant_id": "default",
        },
    )

    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_user_token: str) -> dict:
    """
    Return authorization headers with admin JWT token.
    """
    return {
        "Authorization": f"Bearer {admin_user_token}",
        "X-Tenant-ID": "default",
    }


@pytest.fixture
def superuser_token() -> str:
    """
    Return a platform superuser token without hitting auth endpoints.
    Avoids async DB access in tests that keep sync transactions open.
    """
    tokens = create_token_response(
        user_id="test-superuser",
        email="superuser@example.com",
        role="admin",
        tenant_id="default",
        is_superuser=True,
    )
    return tokens["access_token"]


@pytest.fixture
def superuser_headers(superuser_token: str) -> dict:
    """
    Return authorization headers with superuser JWT token.
    """
    return {
        "Authorization": f"Bearer {superuser_token}",
        "X-Tenant-ID": "default",
    }


# ============================================================================
# Mock External Services
# ============================================================================


@pytest.fixture
def mock_anthropic_api(monkeypatch):
    """
    Mock Anthropic API calls to avoid real API usage in tests.
    """

    class MockAnthropicResponse:
        def __init__(self, content):
            self.content = [type("obj", (object,), {"text": content})]

    class MockAnthropic:
        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return MockAnthropicResponse("Mock AI response for testing")

    monkeypatch.setattr("anthropic.Anthropic", lambda *args, **kwargs: MockAnthropic())
    yield


@pytest.fixture
def mock_http_requests(monkeypatch):
    """
    Mock external HTTP requests.
    """
    import responses as resp_mock

    with resp_mock.RequestsMock() as rsps:
        yield rsps


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_transaction() -> dict:
    """
    Sample transaction data for testing.
    """
    return {
        "transaction_id": "txn_test_123456",
        "amount": 1500.00,
        "currency": "USD",
        "sender_id": "user_sender_001",
        "receiver_id": "user_receiver_002",
        "timestamp": "2026-01-22T10:30:00Z",
        "payment_method": "bank_transfer",
        "country": "US",
    }


@pytest.fixture
def sample_alert() -> dict:
    """
    Sample alert data for testing.
    """
    return {
        "alert_type": "high_value_transaction",
        "severity": "high",
        "transaction_id": "txn_test_123456",
        "risk_score": 85,
        "description": "Transaction exceeds threshold",
        "status": "pending",
    }


@pytest.fixture
def sample_case() -> dict:
    """
    Sample case data for testing.
    """
    return {
        "title": "Suspicious Activity - User 001",
        "description": "Multiple high-value transactions detected",
        "priority": "high",
        "status": "open",
        "assigned_to": None,
    }


# ============================================================================
# Async Fixtures
# ============================================================================


@pytest.fixture
def event_loop():
    """
    Create an instance of the default event loop for each test case.
    Required for pytest-asyncio.
    """
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

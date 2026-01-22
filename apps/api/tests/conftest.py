"""
Pytest configuration and fixtures for YuFeed API tests.
"""
import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from redis import Redis
from opensearchpy import OpenSearch

from src.database import Base, get_db
from src.main import app
from src.config import settings


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create a test database engine with in-memory SQLite for fast testing.
    Use StaticPool to share the same connection across all tests.
    """
    # Use in-memory SQLite for unit tests (fast, isolated)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test.
    Automatically rolls back after each test for isolation.
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    yield session

    # Rollback and cleanup
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with overridden database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db

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
        os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        decode_responses=True
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
        ssl_show_warn=False
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
def test_user_token(client: TestClient) -> str:
    """
    Create a test user and return authentication token.
    """
    # Register test user
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User"
        }
    )

    if response.status_code == 201:
        return response.json()["access_token"]

    # If user already exists, login instead
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
    )

    return response.json()["access_token"]


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """
    Return authorization headers with JWT token.
    """
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_user_token(client: TestClient) -> str:
    """
    Create an admin user and return authentication token.
    """
    response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "full_name": "Admin User",
            "role": "admin"
        }
    )

    if response.status_code == 201:
        return response.json()["access_token"]

    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123!"
        }
    )

    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_user_token: str) -> dict:
    """
    Return authorization headers with admin JWT token.
    """
    return {"Authorization": f"Bearer {admin_user_token}"}


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
            self.content = [type('obj', (object,), {'text': content})]

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
        "country": "US"
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
        "status": "pending"
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
        "assigned_to": None
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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app
from src.models import compliance as comp_models

# Setup Test Database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_kyc_profile(client, admin_headers):
    response = client.post(
        "/api/compliance/kyc",
        json={
            "type": "kyc",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "country": "US"
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["status"] == "pending"
    assert data["risk_level"] == "low"
    assert data["type"] == "kyc"

def test_create_kyb_profile(client, admin_headers):
    response = client.post(
        "/api/compliance/kyb",
        json={
            "type": "kyb",
            "company_name": "Acme Corp",
            "registration_number": "12345678",
            "jurisdiction": "US"
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Acme Corp"
    assert data["type"] == "kyb"

def test_get_cases(client, admin_headers):
    # Create a profile first
    client.post(
        "/api/compliance/kyc",
        json={
            "type": "kyc",
            "first_name": "Alice",
            "last_name": "Wonder",
            "email": "alice@example.com"
        },
        headers=admin_headers,
    )
    
    response = client.get("/api/compliance/cases", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["email"] == "alice@example.com"

def test_review_case(client, admin_headers):
    # Create
    create_res = client.post(
        "/api/compliance/kyc",
        json={
            "type": "kyc",
            "first_name": "Bob",
            "last_name": "Builder",
            "email": "bob@example.com"
        },
        headers=admin_headers,
    )
    profile_id = create_res.json()["id"]
    
    # Review (Approve)
    response = client.post(
        f"/api/compliance/cases/{profile_id}/review",
        json={"action": "approve"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

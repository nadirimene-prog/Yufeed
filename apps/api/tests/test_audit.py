import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app
from src.auth.jwt_handler import JWTHandler


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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _auth_headers(role: str = "admin"):
    token = JWTHandler.create_access_token(
        {"sub": "admin@example.com", "user_id": "admin-1", "role": role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_audit_event_and_decision_flow():
    event_res = client.post(
        "/api/audit/events",
        json={
            "event_type": "txn_fiat",
            "entity_type": "transaction",
            "entity_id": "TX-TEST-1",
            "payload": {"amount": 1000, "currency": "EUR"},
        },
        headers=_auth_headers(),
    )
    assert event_res.status_code == 201
    event_id = event_res.json()["event_id"]

    decision_res = client.post(
        "/api/audit/decisions",
        json={
            "decision": "alert",
            "event_id": event_id,
            "reason_codes": ["RULE-001"],
            "rule_version": "1",
        },
        headers=_auth_headers(),
    )
    assert decision_res.status_code == 201
    decision_id = decision_res.json()["decision_id"]

    get_event = client.get(f"/api/audit/events/{event_id}", headers=_auth_headers())
    assert get_event.status_code == 200
    assert get_event.json()["event_id"] == event_id

    get_decision = client.get(f"/api/audit/decisions/{decision_id}", headers=_auth_headers())
    assert get_decision.status_code == 200
    assert get_decision.json()["decision_id"] == decision_id

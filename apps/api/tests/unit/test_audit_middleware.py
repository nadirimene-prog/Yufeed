import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.audit.middleware import _redact, _parse_json, _extract_entity, audit_log_middleware
from src.audit.models import AuditLog
from src.database import get_db


@pytest.mark.unit
def test_redact_and_parse():
    payload = {"password": "secret", "nested": {"token": "abc", "ok": 1}}
    redacted = _redact(payload)
    assert redacted["password"] == "***"
    assert redacted["nested"]["token"] == "***"

    body = b'{"a": 1}'
    parsed = _parse_json(body, "application/json")
    assert parsed["a"] == 1
    assert _parse_json(b"not-json", "application/json") is None


@pytest.mark.unit
def test_extract_entity():
    entity = _extract_entity("/api/alerts/123")
    assert entity["entity_type"] == "alerts"
    assert entity["entity_id"] == "123"


@pytest.mark.unit
def test_audit_middleware_creates_entry(db_session):
    app = FastAPI()
    app.middleware("http")(audit_log_middleware)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    @app.post("/api/items")
    def create_item():
        return {"ok": True}

    client = TestClient(app)
    resp = client.post("/api/items", json={"name": "x", "password": "secret"})
    assert resp.status_code == 200

    audit = db_session.query(AuditLog).filter(AuditLog.path == "/api/items").first()
    assert audit is not None
    assert audit.path == "/api/items"
    assert audit.action == "post"

import pytest
from datetime import datetime
from fastapi import HTTPException
from starlette.requests import Request

from src.tenancy.context import set_current_tenant, get_current_tenant, clear_current_tenant, TenantContext
from src.tenancy.queries import (
    get_tenant_filtered_query,
    require_tenant,
    ensure_tenant_match,
    set_tenant_on_create,
    tenant_required,
)
from src.tenancy.middleware import TenantMiddleware
from src.models.transaction_models import Transaction


@pytest.mark.unit
def test_tenant_context_helpers():
    clear_current_tenant()
    assert get_current_tenant() is None

    set_current_tenant("tenant_a")
    assert get_current_tenant() == "tenant_a"

    clear_current_tenant()
    assert get_current_tenant() is None

    with TenantContext("tenant_b"):
        assert get_current_tenant() == "tenant_b"
    assert get_current_tenant() is None


@pytest.mark.unit
def test_tenant_query_helpers(db_session):
    clear_current_tenant()
    set_current_tenant("tenant_x")

    tx1 = Transaction(
        tenant_id="tenant_x",
        transaction_id="tx1",
        user_id="user1",
        amount=10,
        currency="USD",
        transaction_type="deposit",
        timestamp=datetime.utcnow(),
        status="completed",
        country_code="US",
    )
    tx2 = Transaction(
        tenant_id="tenant_y",
        transaction_id="tx2",
        user_id="user2",
        amount=20,
        currency="USD",
        transaction_type="deposit",
        timestamp=datetime.utcnow(),
        status="completed",
        country_code="US",
    )
    db_session.add_all([tx1, tx2])
    db_session.commit()

    query = get_tenant_filtered_query(Transaction, db_session)
    rows = query.all()
    assert all(row.tenant_id == "tenant_x" for row in rows)

    ensure_tenant_match(tx1, "tenant_x")
    with pytest.raises(HTTPException):
        ensure_tenant_match(tx1, "tenant_y")

    new_tx = Transaction(
        tenant_id="",
        transaction_id="tx3",
        user_id="user3",
        amount=1,
        currency="USD",
        transaction_type="deposit",
        timestamp=tx1.timestamp,
        status="completed",
        country_code="US",
    )
    set_tenant_on_create(new_tx, "tenant_z")
    assert new_tx.tenant_id == "tenant_z"

    clear_current_tenant()

    with pytest.raises(HTTPException):
        require_tenant()

    set_current_tenant("tenant_req")
    assert require_tenant() == "tenant_req"
    clear_current_tenant()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tenant_required_decorator():
    @tenant_required
    async def handler():
        return "ok"

    clear_current_tenant()
    with pytest.raises(HTTPException):
        await handler()

    set_current_tenant("tenant_ok")
    assert await handler() == "ok"
    clear_current_tenant()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tenant_middleware_helpers(monkeypatch):
    app = lambda scope, receive, send: None
    middleware = TenantMiddleware(app)

    scope = {
        "type": "http",
        "headers": [(b"x-tenant-id", b"tenant_123")],
        "query_string": b"",
        "path": "/",
    }
    request = Request(scope)
    tenant = await middleware._extract_tenant_from_request(request)
    assert tenant == "tenant_123"

    async def fake_extract_api_key(key):
        return "tenant_api"

    monkeypatch.setattr(middleware, "_extract_tenant_from_api_key", fake_extract_api_key)
    scope_api = {
        "type": "http",
        "headers": [(b"x-api-key", b"yk_live_tenant_api_x")],
        "query_string": b"",
        "path": "/",
    }
    request_api = Request(scope_api)
    tenant_api = await middleware._extract_tenant_from_request(request_api)
    assert tenant_api == "tenant_api"

    scope_query = {
        "type": "http",
        "headers": [],
        "query_string": b"tenant_id=tenant_q",
        "path": "/",
    }
    request_query = Request(scope_query)
    tenant_query = await middleware._extract_tenant_from_request(request_query)
    assert tenant_query == "tenant_q"

    scope_default = {
        "type": "http",
        "headers": [],
        "query_string": b"",
        "path": "/",
    }
    request_default = Request(scope_default)
    tenant_default = await middleware._extract_tenant_from_request(request_default)
    assert tenant_default == "default"

    assert middleware._requires_tenant(Request({"type": "http", "path": "/docs", "headers": [], "query_string": b""})) is False
    assert middleware._requires_tenant(Request({"type": "http", "path": "/api/alerts", "headers": [], "query_string": b""})) is True

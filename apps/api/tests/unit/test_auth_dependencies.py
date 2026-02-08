import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.auth.jwt_handler import JWTHandler, PasswordHandler, create_token_response
from src.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_role,
    require_any_role,
    CurrentUser,
)


@pytest.mark.unit
def test_jwt_handler_tokens_and_passwords():
    token = JWTHandler.create_access_token(
        {"sub": "user@example.com", "user_id": "u1", "role": "admin"}
    )
    payload = JWTHandler.decode_token(token)
    assert payload["sub"] == "user@example.com"
    assert JWTHandler.verify_token_type(payload, "access") is True

    refresh = JWTHandler.create_refresh_token(
        {"sub": "user@example.com", "user_id": "u1", "role": "admin"}
    )
    refresh_payload = JWTHandler.decode_token(refresh)
    assert JWTHandler.verify_token_type(refresh_payload, "refresh") is True

    tokens = create_token_response("u1", "user@example.com", role="admin")
    assert "access_token" in tokens and "refresh_token" in tokens

    hashed = PasswordHandler.hash_password("password")
    assert PasswordHandler.verify_password("password", hashed) is True
    assert PasswordHandler.verify_password("wrong", hashed) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_and_optional():
    token = JWTHandler.create_access_token(
        {"sub": "user@example.com", "user_id": "u1", "role": "admin"}
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = await get_current_user(creds)
    assert user.user_id == "u1"
    assert user.has_role("admin") is True

    refresh = JWTHandler.create_refresh_token(
        {"sub": "user@example.com", "user_id": "u1", "role": "admin"}
    )
    bad_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=refresh)
    with pytest.raises(HTTPException):
        await get_current_user(bad_creds)

    assert await get_current_user_optional(None) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_role_helpers():
    user = CurrentUser(user_id="u1", email="user@example.com", role="user")

    admin_required = require_role("admin")
    with pytest.raises(HTTPException):
        await admin_required(current_user=user)

    any_required = require_any_role(["admin", "user"])
    allowed = await any_required(current_user=user)
    assert allowed.user_id == "u1"

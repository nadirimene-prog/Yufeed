"""
Authentication Module

Provides JWT-based authentication for the Yufeed API.
"""

from src.auth.jwt_handler import JWTHandler, PasswordHandler, create_token_response
from src.auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_role,
    require_any_role,
    require_superuser,
    CurrentUser,
)
from src.auth.token_blacklist import TokenBlacklist, token_blacklist

__all__ = [
    "JWTHandler",
    "PasswordHandler",
    "create_token_response",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_any_role",
    "require_superuser",
    "CurrentUser",
    "TokenBlacklist",
    "token_blacklist",
]

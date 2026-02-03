"""
Authentication Dependencies

FastAPI dependencies for protecting endpoints with JWT authentication.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
import logging

from src.auth.jwt_handler import JWTHandler
from src.database import get_db
from src.models.tenant_models import TenantAPIKey, Tenant

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens (allow missing header for API key auth)
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """
    Represents the currently authenticated user.
    Contains user information extracted from JWT token.
    """

    def __init__(self, user_id: str, email: str, role: str, tenant_id: Optional[str] = None, is_superuser: bool = False):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.tenant_id = tenant_id
        self.is_superuser = is_superuser

    def __repr__(self):
        return (
            "CurrentUser("
            f"user_id={self.user_id}, email={self.email}, role={self.role}, "
            f"tenant_id={self.tenant_id}, is_superuser={self.is_superuser}"
            ")"
        )

    def has_role(self, required_role: str) -> bool:
        """Check if user has a specific role."""
        return self.role == required_role

    def has_any_role(self, roles: list) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    request: Request = None,
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        CurrentUser object with user information

    Raises:
        HTTPException: 401 if token is invalid or missing required fields

    Usage:
        ```python
        @router.get("/protected")
        def protected_endpoint(current_user: CurrentUser = Depends(get_current_user)):
            return {"user_id": current_user.user_id}
        ```
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract token from credentials
        token = credentials.credentials if credentials else None

        if token:
            # Decode and validate token
            payload = JWTHandler.decode_token(token)

            # Verify it's an access token
            if not JWTHandler.verify_token_type(payload, "access"):
                logger.warning("Invalid token type provided")
                raise credentials_exception

            # Extract user information
            email: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            role: str = payload.get("role", "user")
            tenant_id: Optional[str] = payload.get("tenant_id")
            is_superuser: bool = bool(payload.get("is_superuser", False))

            if email is None or user_id is None:
                logger.warning("Token missing required fields")
                raise credentials_exception

            logger.debug(f"User authenticated: {email}")
            current_user = CurrentUser(
                user_id=user_id,
                email=email,
                role=role,
                tenant_id=tenant_id,
                is_superuser=is_superuser,
            )
            if request is not None:
                request.state.user = current_user
            return current_user

        # Fallback: API key auth
        api_key = request.headers.get("X-API-Key") if request else None
        if api_key and api_key.startswith("yk_"):
            import hashlib

            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            api_key_record = db.query(TenantAPIKey).filter(
                TenantAPIKey.key_hash == key_hash,
                TenantAPIKey.is_active == True,
            ).first()
            if api_key_record:
                tenant = db.query(Tenant).filter(
                    Tenant.id == api_key_record.tenant_id,
                    Tenant.is_active == True,
                ).first()
                if tenant:
                    current_user = CurrentUser(
                        user_id=f"api_key:{api_key_record.key_prefix}",
                        email="api_key@yufeed.local",
                        role="api_key",
                        tenant_id=tenant.tenant_id,
                        is_superuser=False,
                    )
                    if request is not None:
                        request.state.user = current_user
                    return current_user
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        raise credentials_exception

    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        raise credentials_exception


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None,
) -> Optional[CurrentUser]:
    """
    Dependency to optionally get the current user.
    Returns None if no token is provided, otherwise validates the token.

    Usage:
        ```python
        @router.get("/public-or-protected")
        def endpoint(current_user: Optional[CurrentUser] = Depends(get_current_user_optional)):
            if current_user:
                return {"message": f"Hello {current_user.email}"}
            return {"message": "Hello anonymous user"}
        ```
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials=credentials, request=request)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory to require a specific role.

    Args:
        required_role: The role required to access the endpoint

    Returns:
        Dependency function that checks user role

    Usage:
        ```python
        @router.post("/admin-only")
        def admin_endpoint(current_user: CurrentUser = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
        ```
    """

    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_superuser:
            return current_user
        if not current_user.has_role(required_role):
            logger.warning(
                f"User {current_user.email} attempted to access {required_role}-only endpoint"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_role} role",
            )
        return current_user

    return role_checker


def require_any_role(required_roles: list):
    """
    Dependency factory to require any of the specified roles.

    Args:
        required_roles: List of acceptable roles

    Returns:
        Dependency function that checks user role

    Usage:
        ```python
        @router.post("/admin-or-moderator")
        def endpoint(
            current_user: CurrentUser = Depends(require_any_role(["admin", "moderator"]))
        ):
            return {"message": "Access granted"}
        ```
    """

    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.is_superuser:
            return current_user
        if not current_user.has_any_role(required_roles):
            logger.warning(
                f"User {current_user.email} attempted to access endpoint requiring roles: {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires one of the following roles: {', '.join(required_roles)}",
            )
        return current_user

    return role_checker


def require_superuser():
    """
    Dependency factory to require platform superuser privileges.
    """

    async def superuser_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.is_superuser:
            logger.warning(
                f"User {current_user.email} attempted to access superuser-only endpoint"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires superuser privileges",
            )
        return current_user

    return superuser_checker


class RateLimiter:
    """
    Simple in-memory rate limiter for endpoints.
    For production, use Redis-based rate limiting.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # In production, use Redis

    async def check_rate_limit(
        self,
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        """
        Check if user has exceeded rate limit.

        Usage:
            ```python
            rate_limiter = RateLimiter(requests_per_minute=10)

            @router.post("/rate-limited")
            def endpoint(current_user: CurrentUser = Depends(rate_limiter.check_rate_limit)):
                return {"message": "Success"}
            ```
        """
        # TODO: Implement Redis-based rate limiting
        # For now, just return the user
        return current_user

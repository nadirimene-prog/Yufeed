"""
Authentication API Endpoints

Handles user login, token refresh, registration, and password reset.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import Optional
import logging
import re

from datetime import timedelta

from src.config import settings
from src.database import get_async_db
from src.models.user import User
from src.models.tenant_models import TenantUser, Tenant
from src.auth.jwt_handler import JWTHandler, PasswordHandler, create_token_response
from src.auth.dependencies import get_current_user, CurrentUser
from src.auth.token_blacklist import token_blacklist
from src.middleware import limiter, RateLimits
from src.services.email import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Password validation
MIN_PASSWORD_LENGTH = 8
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


# Request/Response Models
class UserRegister(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        return v


class UserLogin(BaseModel):
    """User login request."""

    email: EmailStr
    password: str
    tenant_id: Optional[str] = None


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserProfile(BaseModel):
    """User profile response."""

    user_id: str
    email: str
    role: str
    full_name: Optional[str] = None
    is_verified: bool = False


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        return v


class ForgotPasswordRequest(BaseModel):
    """Forgot-password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset-password request."""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        return v


# Password reset token configuration
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 15


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def _fetch_user_tenants(db: AsyncSession, user: User) -> dict:
    identifiers = {str(user.id)}
    if user.email:
        identifiers.add(user.email.lower())

    stmt = (
        select(TenantUser, Tenant)
        .join(Tenant, Tenant.id == TenantUser.tenant_id)
        .where(
            TenantUser.user_id.in_(identifiers),
            TenantUser.is_active.is_(True),
            Tenant.is_active.is_(True),
            Tenant.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    rows = result.all()

    tenants = {}
    for tenant_user, tenant in rows:
        tenants[tenant.tenant_id] = {
            "tenant": tenant,
            "role": tenant_user.role,
        }
    return tenants


async def _resolve_tenant_context(
    db: AsyncSession,
    user: User,
    requested_tenant_id: Optional[str],
) -> tuple[Optional[str], str]:
    tenants = await _fetch_user_tenants(db, user)

    if requested_tenant_id:
        if user.is_superuser:
            tenant = await db.execute(
                select(Tenant).where(
                    Tenant.tenant_id == requested_tenant_id,
                    Tenant.is_active.is_(True),
                    Tenant.deleted_at.is_(None),
                )
            )
            tenant_obj = tenant.scalar_one_or_none()
            if not tenant_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
                )
            return requested_tenant_id, "admin"

        match = tenants.get(requested_tenant_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of the requested tenant",
            )
        return requested_tenant_id, match["role"]

    if len(tenants) == 1:
        tenant_id, match = next(iter(tenants.items()))
        return tenant_id, match["role"]

    if len(tenants) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Tenant selection required",
                "available_tenants": sorted(tenants.keys()),
            },
        )

    if user.is_superuser:
        result = await db.execute(
            select(Tenant.tenant_id).where(
                Tenant.is_active.is_(True),
                Tenant.deleted_at.is_(None),
            )
        )
        tenant_ids = sorted({row[0] for row in result.all() if row and row[0]})
        if len(tenant_ids) == 1:
            return tenant_ids[0], "admin"
        if len(tenant_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Tenant selection required",
                    "available_tenants": tenant_ids,
                },
            )
        return None, "admin"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No active tenant membership found for user",
    )


async def _ensure_tenant_access(db: AsyncSession, user: User, tenant_id: Optional[str]) -> None:
    if not tenant_id:
        if user.is_superuser:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context is required for this user",
        )

    if user.is_superuser:
        tenant = await db.execute(
            select(Tenant).where(
                Tenant.tenant_id == tenant_id,
                Tenant.is_active.is_(True),
                Tenant.deleted_at.is_(None),
            )
        )
        if not tenant.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return

    tenants = await _fetch_user_tenants(db, user)
    if tenant_id not in tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of the requested tenant",
        )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.AUTH_REGISTER)
async def register(
    request: Request, user_data: UserRegister, db: AsyncSession = Depends(get_async_db)
):
    """
    Register a new user account.

    Creates a new user with hashed password and returns JWT tokens.
    """
    logger.info(f"User registration attempt: {user_data.email}")

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.warning(f"Registration failed - email already exists: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    hashed_password = PasswordHandler.hash_password(user_data.password)

    new_user = User(
        email=user_data.email.lower(),
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        default_role="user",
        is_active=True,
        is_verified=False,  # Email verification not implemented yet
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        logger.error(f"Database integrity error during registration: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    logger.info(f"User registered successfully: {user_data.email} (id={new_user.id})")

    # Create tokens
    tokens = create_token_response(
        user_id=str(new_user.id), email=new_user.email, role=new_user.default_role
    )

    return tokens


@router.post("/login", response_model=TokenResponse)
@limiter.limit(RateLimits.AUTH_LOGIN)
async def login(request: Request, login_data: UserLogin, db: AsyncSession = Depends(get_async_db)):
    """
    Authenticate user and return JWT tokens.

    Validates credentials and implements account lockout after failed attempts.
    """
    logger.info(f"Login attempt: {login_data.email}")

    # Query user from database
    result = await db.execute(select(User).where(User.email == login_data.email.lower()))
    user = result.scalar_one_or_none()

    # User not found
    if not user:
        logger.warning(f"Login failed - user not found: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if account is locked
    if user.is_locked:
        logger.warning(f"Login failed - account locked: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                "Account is temporarily locked due to too many failed login attempts. "
                "Please try again later."
            ),
        )

    # Check if account is active
    if not user.is_active:
        logger.warning(f"Login failed - account inactive: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )

    # Verify password
    if not PasswordHandler.verify_password(login_data.password, user.hashed_password):
        # Increment failed login counter
        user.increment_failed_login()
        await db.commit()

        logger.warning(
            f"Login failed - incorrect password: {login_data.email} "
            f"(attempt {user.failed_login_attempts})"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Successful login - record and reset counters
    client_ip = get_client_ip(request)
    user.record_login(ip_address=client_ip)
    await db.commit()

    logger.info(f"User logged in successfully: {login_data.email}")

    # Resolve tenant context (default if exactly one)
    tenant_id, tenant_role = await _resolve_tenant_context(db, user, login_data.tenant_id)

    # Create tokens
    tokens = create_token_response(
        user_id=str(user.id),
        email=user.email,
        role=tenant_role or user.default_role,
        tenant_id=tenant_id,
        is_superuser=user.is_superuser,
    )

    return tokens


@router.post("/token", response_model=TokenResponse)
@limiter.limit(RateLimits.AUTH_LOGIN)
async def login_oauth(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    """
    OAuth2-compatible token endpoint for login.

    Uses username/password fields from OAuth2 spec.
    Username is treated as email address.
    """
    login_data = UserLogin(
        email=form_data.username, password=form_data.password  # OAuth2 uses 'username' field
    )

    return await login(request, login_data, db)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(RateLimits.AUTH_REFRESH)
async def refresh_token(
    request: Request, refresh_data: TokenRefresh, db: AsyncSession = Depends(get_async_db)
):
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    try:
        # Decode refresh token
        payload = JWTHandler.decode_token(refresh_data.refresh_token)

        # Verify it's a refresh token
        if not JWTHandler.verify_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Check if refresh token has been revoked
        refresh_jti = payload.get("jti")
        refresh_user_id = payload.get("user_id")
        refresh_iat = int(payload.get("iat", 0))
        if refresh_jti and token_blacklist.is_token_revoked(
            jti=refresh_jti,
            user_id=str(refresh_user_id) if refresh_user_id else "",
            issued_at=refresh_iat,
        ):
            logger.warning(f"Revoked refresh token used: jti={refresh_jti}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        # Extract user information
        email = payload.get("sub")
        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")

        if not email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        # Verify user still exists and is active
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        await _ensure_tenant_access(db, user, tenant_id)

        role = user.default_role
        if tenant_id:
            if user.is_superuser:
                role = "admin"
            else:
                tenants = await _fetch_user_tenants(db, user)
                role = tenants.get(tenant_id, {}).get("role", role)

        logger.info(f"Token refreshed for user: {email}")

        # Create new tokens
        tokens = create_token_response(
            user_id=str(user.id),
            email=user.email,
            role=role,
            tenant_id=tenant_id,
            is_superuser=user.is_superuser,
        )

        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
        )


@router.get("/me", response_model=UserProfile)
@limiter.limit(RateLimits.READ)
async def get_current_user_profile(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get current authenticated user's profile.

    Requires valid JWT access token.
    """
    logger.debug(f"Profile requested: {current_user.email}")

    # Query full user profile from database
    result = await db.execute(select(User).where(User.id == int(current_user.user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfile(
        user_id=str(user.id),
        email=user.email,
        role=current_user.role,
        full_name=user.full_name,
        is_verified=user.is_verified,
    )


@router.post("/logout", response_model=MessageResponse)
@limiter.limit(RateLimits.UPDATE)
async def logout(request: Request, current_user: CurrentUser = Depends(get_current_user)):
    """
    Logout current user.

    Revokes the current access token by adding its JTI to the Redis
    blacklist. The blacklist entry auto-expires when the JWT would
    have expired, keeping Redis usage bounded.
    """
    import time

    # Extract the raw token from the Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

    revoked = False
    if token:
        try:
            payload = JWTHandler.decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            remaining_ttl = max(int(exp) - int(time.time()), 1)

            if jti:
                revoked = token_blacklist.revoke_token(jti, remaining_ttl)
        except Exception as e:
            logger.warning(f"Could not revoke token during logout: {e}")

    logger.info(f"User logged out: {current_user.email} (token_revoked={revoked})")

    return MessageResponse(message="Successfully logged out.")


@router.post("/logout-all", response_model=MessageResponse)
@limiter.limit(RateLimits.UPDATE)
async def logout_all(request: Request, current_user: CurrentUser = Depends(get_current_user)):
    """
    Revoke all active tokens for the current user.

    Every token issued before this moment will be rejected. Useful when
    a user suspects their credentials have been compromised.
    """
    revoked = token_blacklist.revoke_all_user_tokens(current_user.user_id)
    logger.info(f"All tokens revoked for user: {current_user.email} (success={revoked})")

    return MessageResponse(message="All sessions have been terminated.")


@router.post("/change-password", response_model=MessageResponse)
@limiter.limit(RateLimits.UPDATE)
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Change the current user's password.

    Requires current password verification.
    """
    # Get user from database
    result = await db.execute(select(User).where(User.id == int(current_user.user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify current password
    if not PasswordHandler.verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
        )

    # Update password
    from datetime import datetime, timezone

    user.hashed_password = PasswordHandler.hash_password(password_data.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Password changed for user: {current_user.email}")

    return MessageResponse(message="Password changed successfully")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(RateLimits.AUTH_FORGOT_PASSWORD)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Request a password reset email.

    Generates a short-lived reset token and emails it to the user.
    Always returns a 200 with a generic message regardless of whether the
    email exists, to prevent user-enumeration attacks.
    """
    # Always return the same response to prevent user enumeration
    generic_response = MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user:
        logger.info(f"Password reset requested for non-existent email: {body.email}")
        return generic_response

    if not user.is_active:
        logger.info(f"Password reset requested for inactive account: {body.email}")
        return generic_response

    # Create a short-lived password-reset JWT.
    # We use "purpose" (not "type") because create_access_token
    # unconditionally sets type="access".
    reset_token = JWTHandler.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "purpose": "password_reset",
        },
        expires_delta=timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )

    # Build the frontend reset URL
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"

    # Send the email (fire-and-forget; failure is logged but does not crash)
    EmailService.send_password_reset_email(
        email=user.email,
        reset_token=reset_token,
        reset_url=reset_url,
    )

    logger.info(f"Password reset email sent for user: {user.email}")
    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(RateLimits.AUTH_RESET_PASSWORD)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reset a user's password using a valid reset token.

    Validates the token purpose, expiry, and user existence before
    updating the password.
    """
    # Decode and validate the reset token
    try:
        payload = JWTHandler.decode_token(body.token)
    except Exception:
        logger.warning("Password reset failed: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Verify this token was issued for a password reset
    if payload.get("purpose") != "password_reset":
        logger.warning("Password reset failed: wrong token purpose")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Extract user ID from the token (stored in "sub")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Look up the user
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is deactivated. Please contact support.",
        )

    # Update password
    from datetime import datetime, timezone

    user.hashed_password = PasswordHandler.hash_password(body.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Password reset completed for user: {user.email}")

    return MessageResponse(
        message="Password has been reset successfully. You can now log in with your new password."
    )

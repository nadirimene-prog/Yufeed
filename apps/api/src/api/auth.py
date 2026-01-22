"""
Authentication API Endpoints

Handles user login, token refresh, and user registration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional
import logging

from src.database import get_db
from src.auth.jwt_handler import (
    JWTHandler,
    PasswordHandler,
    create_token_response
)
from src.auth.dependencies import get_current_user, CurrentUser
from src.middleware import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.AUTH_REGISTER)
def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    **Note:** This is a basic implementation. In production, you should:
    - Add email verification
    - Implement CAPTCHA to prevent bot registrations
    - Add rate limiting
    - Validate password strength
    """
    # TODO: Implement actual user creation in database
    # For now, this is a placeholder that returns mock tokens

    logger.info(f"User registration attempt: {user_data.email}")

    # Check if user already exists (placeholder)
    # In production: query database for existing user

    # Hash the password
    hashed_password = PasswordHandler.hash_password(user_data.password)

    # Create user in database (placeholder)
    # In production: create User model and save to database
    user_id = "mock-user-id-123"  # Replace with actual user ID from database

    logger.info(f"User registered successfully: {user_data.email}")

    # Create tokens
    tokens = create_token_response(
        user_id=user_id,
        email=user_data.email,
        role="user"
    )

    return tokens


@router.post("/login", response_model=TokenResponse)
@limiter.limit(RateLimits.AUTH_LOGIN)
def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.

    **Note:** This is a basic implementation. In production, you should:
    - Add rate limiting to prevent brute force attacks
    - Log failed login attempts
    - Implement account lockout after X failed attempts
    - Add 2FA support
    """
    logger.info(f"Login attempt: {login_data.email}")

    # TODO: Query database for user
    # In production: db.query(User).filter(User.email == login_data.email).first()

    # Mock user data (replace with actual database query)
    mock_user = {
        "user_id": "mock-user-id-123",
        "email": login_data.email,
        "hashed_password": PasswordHandler.hash_password("password123"),  # Mock password
        "role": "user"
    }

    # Verify password
    if not PasswordHandler.verify_password(login_data.password, mock_user["hashed_password"]):
        logger.warning(f"Failed login attempt: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    logger.info(f"User logged in successfully: {login_data.email}")

    # Create tokens
    tokens = create_token_response(
        user_id=mock_user["user_id"],
        email=mock_user["email"],
        role=mock_user["role"]
    )

    return tokens


@router.post("/token", response_model=TokenResponse)
@limiter.limit(RateLimits.AUTH_LOGIN)
def login_oauth(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2-compatible token endpoint for login.

    Uses username/password fields from OAuth2 spec.
    Username is treated as email address.
    """
    login_data = UserLogin(
        email=form_data.username,  # OAuth2 uses 'username' field
        password=form_data.password
    )

    return login(request, login_data, db)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(RateLimits.AUTH_REFRESH)
def refresh_token(
    request: Request,
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
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

        # Extract user information
        email = payload.get("sub")
        user_id = payload.get("user_id")
        role = payload.get("role", "user")

        if not email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        logger.info(f"Token refreshed for user: {email}")

        # Create new tokens
        tokens = create_token_response(
            user_id=user_id,
            email=email,
            role=role
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
def get_current_user_profile(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Get current authenticated user's profile.

    Requires valid JWT access token.
    """
    logger.debug(f"Profile requested: {current_user.email}")

    # TODO: Query database for full user profile
    # In production: db.query(User).filter(User.id == current_user.user_id).first()

    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        full_name="John Doe"  # Replace with actual data from database
    )


@router.post("/logout")
@limiter.limit(RateLimits.UPDATE)
def logout(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Logout current user.

    **Note:** JWTs are stateless, so we can't truly "logout" without a token blacklist.
    In production, implement token blacklist using Redis:
    - Store revoked tokens in Redis with expiration = token expiration
    - Check blacklist in authentication middleware
    """
    logger.info(f"User logged out: {current_user.email}")

    # TODO: Add token to blacklist in Redis
    # redis_client.setex(f"blacklist:{token}", expiration_seconds, "true")

    return {
        "message": "Successfully logged out",
        "note": "Token will remain valid until expiration. Implement token blacklist for immediate revocation."
    }

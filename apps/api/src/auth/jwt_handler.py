"""
JWT Authentication Handler

Provides token generation, validation, and user authentication for the API.
Uses python-jose for JWT encoding/decoding.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
import logging
import uuid

from src.config import settings


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = getattr(settings, "SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class JWTHandler:
    """Handles JWT token creation and validation."""

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a new JWT access token.

        Args:
            data: Dictionary containing user data (typically user_id, email, role)
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string

        Example:
            >>> token = JWTHandler.create_access_token({"sub": "user@example.com", "role": "admin"})
        """
        to_encode = data.copy()

        if expires_delta:
            expire = utc_now() + expires_delta
        else:
            expire = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update(
            {
                "exp": expire,
                "iat": utc_now(),
                "type": "access",
                "jti": str(uuid.uuid4()),
            }
        )

        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            logger.debug(f"Access token created for subject: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a new JWT refresh token with longer expiration.

        Args:
            data: Dictionary containing user data

        Returns:
            Encoded JWT refresh token string
        """
        to_encode = data.copy()
        expire = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update(
            {
                "exp": expire,
                "iat": utc_now(),
                "type": "refresh",
                "jti": str(uuid.uuid4()),
            }
        )

        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            logger.debug(f"Refresh token created for subject: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise

    @staticmethod
    def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
        """
        Verify the token type (access or refresh).

        Args:
            payload: Decoded token payload
            expected_type: Expected token type ("access" or "refresh")

        Returns:
            True if token type matches, False otherwise
        """
        token_type = payload.get("type")
        return token_type == expected_type


class PasswordHandler:
    """Handles password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain text password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string

        Note:
            Bcrypt has a maximum password length of 72 bytes.
            Longer passwords will be truncated.
        """
        # Convert to bytes and hash
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_token_response(
    user_id: str,
    email: str,
    role: str = "user",
    tenant_id: Optional[str] = None,
    is_superuser: bool = False,
) -> Dict[str, str]:
    """
    Create a complete token response with both access and refresh tokens.

    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role (default: "user")

    Returns:
        Dictionary containing access_token, refresh_token, and token_type

    Example:
        >>> tokens = create_token_response("123", "user@example.com", "admin")
        >>> tokens["access_token"]  # JWT access token
        >>> tokens["refresh_token"]  # JWT refresh token
    """
    token_data = {"sub": email, "user_id": user_id, "role": role}
    if tenant_id:
        token_data["tenant_id"] = tenant_id
    if is_superuser:
        token_data["is_superuser"] = True

    access_token = JWTHandler.create_access_token(token_data)
    refresh_token = JWTHandler.create_refresh_token(token_data)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

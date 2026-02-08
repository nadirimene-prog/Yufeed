"""
User Authentication Models

Stores user credentials and profile information for authentication.
"""

from sqlalchemy import Column, Integer, String, Boolean, Index, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    User model for authentication.

    Stores credentials and basic profile information.
    User-tenant relationships are managed by TenantUser.
    """

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email_lower", "email"),)  # For case-insensitive lookup

    id = Column(Integer, primary_key=True)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(255))
    avatar_url = Column(String(500))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Email verified
    is_superuser = Column(Boolean, default=False, nullable=False)  # Platform admin

    # Default role (can be overridden per-tenant via TenantUser)
    default_role = Column(String(50), default="user")  # 'user', 'analyst', 'compliance', 'admin'

    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(TIMESTAMP(timezone=True))  # Account lockout
    last_login_at = Column(TIMESTAMP(timezone=True))
    last_login_ip = Column(String(45))
    password_changed_at = Column(TIMESTAMP(timezone=True))

    # Preferences
    preferences = Column(
        JSON().with_variant(JSONB(), "postgresql")
    )  # User preferences (theme, notifications, etc.)

    # Timestamps - explicitly timezone-aware
    created_at = Column(TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def increment_failed_login(self, max_attempts: int = 5, lockout_minutes: int = 15):
        """Increment failed login counter and lock if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            from datetime import timedelta

            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)

    def reset_failed_login(self):
        """Reset failed login counter after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def record_login(self, ip_address: str = None):
        """Record successful login."""
        self.last_login_at = datetime.now(timezone.utc)
        if ip_address:
            self.last_login_ip = ip_address
        self.reset_failed_login()

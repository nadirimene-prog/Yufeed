"""
Tenant Models
Phase 4C: Task 7 - Multi-Tenancy Support

Models for multi-tenant architecture with complete tenant isolation.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from src.database import Base


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class Tenant(Base):
    """
    Tenant model for multi-tenancy.

    Each tenant represents an organization using the platform
    (e.g., a bank, fintech, or compliance firm).
    """

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    tier = Column(String(50), default="standard")  # 'free', 'standard', 'enterprise'

    # Contact information
    contact_email = Column(String(255))
    contact_name = Column(String(255))

    # Regulatory profile
    institution_type = Column(String(50))  # 'pi', 'emi', 'vasp', 'credit_institution'
    license_number = Column(String(255))
    license_jurisdiction = Column(String(10))  # ISO country code
    supervisory_authority = Column(String(255))
    regulatory_scope_tags = Column(JSON().with_variant(JSONB(), "postgresql"))

    # Configuration
    settings = Column(JSON().with_variant(JSONB(), "postgresql"))  # Tenant-specific settings
    rate_limits = Column(JSON().with_variant(JSONB(), "postgresql"))  # Per-tenant rate limits
    feature_flags = Column(JSON().with_variant(JSONB(), "postgresql"))  # Feature toggles

    # Branding
    logo_url = Column(String(500))
    primary_color = Column(String(7))  # Hex color code
    secondary_color = Column(String(7))

    # Metadata
    metadata_json = Column("metadata", JSON().with_variant(JSONB(), "postgresql"))

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    deleted_at = Column(DateTime)  # Soft delete

    # Relationships
    api_keys = relationship("TenantAPIKey", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    regulatory_profiles = relationship(
        "TenantRegulatoryProfile",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class TenantRegulatoryProfile(Base):
    """
    Per-tenant applicability overrides for regulatory documents.

    Regulatory obligations remain global. This model captures whether a
    specific regulation is fully applicable, partially applicable, or exempt
    for a given tenant.
    """

    __tablename__ = "tenant_regulatory_profiles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "regulation_doc_id", name="uq_tenant_regulatory_profile"),
    )

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    regulation_doc_id = Column(
        Integer, ForeignKey("legal_documents.id"), nullable=False, index=True
    )
    applicability = Column(String(20), nullable=False, default="full")  # full | partial | exempt
    applicability_notes = Column(Text)
    effective_from = Column(DateTime)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tenant = relationship("Tenant", back_populates="regulatory_profiles")
    regulation = relationship("LegalDocument")


class TenantAPIKey(Base):
    """
    API Keys for tenant authentication.

    Format: yk_live_<tenant_id>_<random>
    Example: yk_live_acme_corp_a1b2c3d4e5f6
    """

    __tablename__ = "tenant_api_keys"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # API Key
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # SHA-256 hash
    key_prefix = Column(String(20), nullable=False)  # First few chars for identification

    # Metadata
    name = Column(String(255))  # Friendly name for the key
    description = Column(Text)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)

    # Permissions
    scopes = Column(
        JSON().with_variant(JSONB(), "postgresql")
    )  # API scopes ['read:alerts', 'write:cases']

    # Security
    created_by = Column(String(255))
    expires_at = Column(DateTime)  # Optional expiration

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    revoked_at = Column(DateTime)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")


class TenantUser(Base):
    """
    User-Tenant association with roles.

    Supports users belonging to multiple tenants with different roles.
    """

    __tablename__ = "tenant_users"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Role in this tenant
    role = Column(String(50), default="viewer")  # 'admin', 'analyst', 'viewer'

    # Permissions
    permissions = Column(JSON().with_variant(JSONB(), "postgresql"))

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")


class TenantAuditLog(Base):
    """
    Audit log for tenant-level actions.

    Tracks administrative actions like creating API keys, changing settings, etc.
    """

    __tablename__ = "tenant_audit_logs"
    __table_args__ = (Index("ix_tenant_audit_logs_tenant_created", "tenant_id", "created_at"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # Action details
    action_type = Column(String(100), nullable=False)  # 'api_key_created', 'settings_updated'
    actor_user_id = Column(String(255))  # Who performed the action

    # Details
    description = Column(Text)
    details = Column(JSON().with_variant(JSONB(), "postgresql"))

    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)

    # Timestamp
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

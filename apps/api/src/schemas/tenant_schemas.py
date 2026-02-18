"""
Tenant Pydantic Schemas
Phase 4C: Task 7.3 & 7.4 - Tenant Management API

Request/response schemas for tenant and API key management.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


VALID_INSTITUTION_TYPES = {"pi", "emi", "vasp", "credit_institution"}
VALID_APPLICABILITY = {"full", "partial", "exempt"}

# ============================================================================
# TENANT SCHEMAS
# ============================================================================


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    tier: str = Field(default="standard", max_length=50)
    institution_type: Optional[str] = Field(None, max_length=50)
    license_number: Optional[str] = Field(None, max_length=255)
    license_jurisdiction: Optional[str] = Field(None, max_length=10)
    supervisory_authority: Optional[str] = Field(None, max_length=255)
    regulatory_scope_tags: Optional[List[str]] = None
    primary_color: Optional[str] = Field(None, max_length=7)
    secondary_color: Optional[str] = Field(None, max_length=7)
    logo_url: Optional[str] = Field(None, max_length=500)

    @validator("primary_color", "secondary_color")
    def validate_hex_color(cls, v):
        if v and not v.startswith("#"):
            raise ValueError("Color must be a hex code starting with #")
        if v and len(v) != 7:
            raise ValueError("Color must be 7 characters (#RRGGBB)")
        return v

    @validator("tier")
    def validate_tier(cls, v):
        allowed_tiers = ["free", "standard", "enterprise"]
        if v not in allowed_tiers:
            raise ValueError(f'Tier must be one of: {", ".join(allowed_tiers)}')
        return v

    @validator("institution_type")
    def validate_institution_type(cls, v):
        if v is None:
            return None
        normalized = v.strip().lower()
        if normalized not in VALID_INSTITUTION_TYPES:
            allowed = ", ".join(sorted(VALID_INSTITUTION_TYPES))
            raise ValueError(f"institution_type must be one of: {allowed}")
        return normalized

    @validator("license_jurisdiction")
    def validate_license_jurisdiction(cls, v):
        if v is None:
            return None
        return v.strip().upper()


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""

    tenant_id: str = Field(..., min_length=3, max_length=255, pattern=r"^[a-z0-9_]+$")

    @validator("tenant_id")
    def validate_tenant_id(cls, v):
        # Reserved tenant IDs
        reserved = ["default", "admin", "system", "api", "public"]
        if v in reserved:
            raise ValueError(f'Tenant ID "{v}" is reserved')
        return v


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    primary_color: Optional[str] = Field(None, max_length=7)
    secondary_color: Optional[str] = Field(None, max_length=7)
    logo_url: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, Any]] = None
    institution_type: Optional[str] = None
    license_number: Optional[str] = None
    license_jurisdiction: Optional[str] = None
    supervisory_authority: Optional[str] = None
    regulatory_scope_tags: Optional[List[str]] = None

    @validator("institution_type")
    def validate_update_institution_type(cls, v):
        if v is None:
            return None
        normalized = v.strip().lower()
        if normalized not in VALID_INSTITUTION_TYPES:
            allowed = ", ".join(sorted(VALID_INSTITUTION_TYPES))
            raise ValueError(f"institution_type must be one of: {allowed}")
        return normalized

    @validator("license_jurisdiction")
    def validate_update_license_jurisdiction(cls, v):
        if v is None:
            return None
        return v.strip().upper()


class TenantResponse(TenantBase):
    """Schema for tenant API response."""

    id: int
    tenant_id: str
    is_active: bool
    settings: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_json")
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class TenantStats(BaseModel):
    """Schema for tenant statistics."""

    tenant_id: str
    total_transactions: int
    total_alerts: int
    total_cases: int
    total_users: int
    active_api_keys: int
    api_calls_today: int
    storage_used_mb: float


# ============================================================================
# API KEY SCHEMAS
# ============================================================================


class APIKeyBase(BaseModel):
    """Base API key schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key."""

    pass


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    scopes: Optional[List[str]] = None


class APIKeyResponse(APIKeyBase):
    """Schema for API key response (without the actual key)."""

    id: int
    tenant_id: int
    key_prefix: str  # First few characters for identification
    is_active: bool
    last_used_at: Optional[datetime] = None
    usage_count: int
    created_by: Optional[str] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes the actual key)."""

    api_key: str  # Full API key - only shown once at creation


class APIKeyRotateResponse(BaseModel):
    """Schema for API key rotation response."""

    old_key_id: int
    new_key: APIKeyCreateResponse
    message: str


# ============================================================================
# TENANT USER SCHEMAS
# ============================================================================


class TenantUserBase(BaseModel):
    """Base tenant user schema."""

    user_id: str = Field(..., max_length=255)
    role: str = Field(default="viewer", max_length=50)
    permissions: Optional[Dict[str, Any]] = None

    @validator("role")
    def validate_role(cls, v):
        allowed_roles = ["admin", "analyst", "viewer"]
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class TenantUserCreate(TenantUserBase):
    """Schema for adding a user to a tenant."""

    pass


class TenantUserUpdate(BaseModel):
    """Schema for updating a tenant user."""

    role: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None


class TenantUserResponse(TenantUserBase):
    """Schema for tenant user response."""

    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# TENANT CONFIGURATION SCHEMAS
# ============================================================================


class RateLimitConfig(BaseModel):
    """Schema for rate limit configuration."""

    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    requests_per_hour: int = Field(default=1000, ge=1, le=100000)
    requests_per_day: int = Field(default=10000, ge=1, le=1000000)
    burst_size: int = Field(default=10, ge=1, le=100)


class FeatureFlagConfig(BaseModel):
    """Schema for feature flag configuration."""

    ml_auto_triage: bool = Field(default=True)
    websocket_notifications: bool = Field(default=True)
    graphql_api: bool = Field(default=False)
    graph_analytics: bool = Field(default=False)
    advanced_reporting: bool = Field(default=True)
    api_webhooks: bool = Field(default=False)
    custom_rules: bool = Field(default=True)


class TenantSettings(BaseModel):
    """Schema for tenant settings."""

    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD", max_length=3)
    language: str = Field(default="en", max_length=2)
    notification_email: Optional[str] = None
    webhook_url: Optional[str] = None
    data_retention_days: int = Field(default=90, ge=30, le=3650)
    alert_threshold_override: Optional[Dict[str, Any]] = None


class TenantConfigUpdate(BaseModel):
    """Schema for updating tenant configuration."""

    settings: Optional[TenantSettings] = None
    rate_limits: Optional[RateLimitConfig] = None
    feature_flags: Optional[FeatureFlagConfig] = None


# ============================================================================
# TENANT REGULATORY PROFILE SCHEMAS
# ============================================================================


class TenantRegulatoryProfileUpdate(BaseModel):
    """Schema for updating tenant regulatory profile fields."""

    institution_type: Optional[str] = Field(None, max_length=50)
    license_number: Optional[str] = Field(None, max_length=255)
    license_jurisdiction: Optional[str] = Field(None, max_length=10)
    supervisory_authority: Optional[str] = Field(None, max_length=255)
    regulatory_scope_tags: Optional[List[str]] = None

    @validator("institution_type")
    def validate_institution_type(cls, v):
        if v is None:
            return None
        normalized = v.strip().lower()
        if normalized not in VALID_INSTITUTION_TYPES:
            allowed = ", ".join(sorted(VALID_INSTITUTION_TYPES))
            raise ValueError(f"institution_type must be one of: {allowed}")
        return normalized

    @validator("license_jurisdiction")
    def validate_license_jurisdiction(cls, v):
        if v is None:
            return None
        return v.strip().upper()


class TenantRegulationAssignment(BaseModel):
    """Schema for adding/updating/removing regulation applicability for a tenant."""

    regulation_doc_id: int = Field(..., gt=0)
    applicability: str = Field(default="full", max_length=20)
    applicability_notes: Optional[str] = None
    effective_from: Optional[datetime] = None
    remove: bool = False

    @validator("applicability")
    def validate_applicability(cls, v):
        normalized = v.strip().lower()
        if normalized not in VALID_APPLICABILITY:
            allowed = ", ".join(sorted(VALID_APPLICABILITY))
            raise ValueError(f"applicability must be one of: {allowed}")
        return normalized


class TenantRegulationAssignmentResponse(BaseModel):
    """Response for tenant regulation assignment endpoint."""

    tenant_id: str
    regulation_doc_id: int
    applicability: Optional[str] = None
    applicability_notes: Optional[str] = None
    effective_from: Optional[datetime] = None
    created: bool = False
    removed: bool = False


class ApplicableRegulationResponse(BaseModel):
    """Applicable regulation summary for a tenant."""

    regulation_doc_id: int
    celex: str
    title: str
    publication_date: Optional[datetime] = None
    scope_tags: List[str] = Field(default_factory=list)
    applicability: str
    applicability_source: str
    applicability_notes: Optional[str] = None
    effective_from: Optional[datetime] = None

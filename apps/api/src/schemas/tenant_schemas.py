"""
Tenant Pydantic Schemas
Phase 4C: Task 7.3 & 7.4 - Tenant Management API

Request/response schemas for tenant and API key management.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


# ============================================================================
# TENANT SCHEMAS
# ============================================================================

class TenantBase(BaseModel):
    """Base tenant schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=255)
    tier: str = Field(default='standard', max_length=50)
    primary_color: Optional[str] = Field(None, max_length=7)
    secondary_color: Optional[str] = Field(None, max_length=7)
    logo_url: Optional[str] = Field(None, max_length=500)

    @validator('primary_color', 'secondary_color')
    def validate_hex_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a hex code starting with #')
        if v and len(v) != 7:
            raise ValueError('Color must be 7 characters (#RRGGBB)')
        return v

    @validator('tier')
    def validate_tier(cls, v):
        allowed_tiers = ['free', 'standard', 'enterprise']
        if v not in allowed_tiers:
            raise ValueError(f'Tier must be one of: {", ".join(allowed_tiers)}')
        return v


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    tenant_id: str = Field(..., min_length=3, max_length=255, pattern=r'^[a-z0-9_]+$')

    @validator('tenant_id')
    def validate_tenant_id(cls, v):
        # Reserved tenant IDs
        reserved = ['default', 'admin', 'system', 'api', 'public']
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


class TenantResponse(TenantBase):
    """Schema for tenant API response."""
    id: int
    tenant_id: str
    is_active: bool
    settings: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    feature_flags: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    role: str = Field(default='viewer', max_length=50)
    permissions: Optional[Dict[str, Any]] = None

    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'analyst', 'viewer']
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
    timezone: str = Field(default='UTC')
    currency: str = Field(default='USD', max_length=3)
    language: str = Field(default='en', max_length=2)
    notification_email: Optional[str] = None
    webhook_url: Optional[str] = None
    data_retention_days: int = Field(default=90, ge=30, le=3650)
    alert_threshold_override: Optional[Dict[str, Any]] = None


class TenantConfigUpdate(BaseModel):
    """Schema for updating tenant configuration."""
    settings: Optional[TenantSettings] = None
    rate_limits: Optional[RateLimitConfig] = None
    feature_flags: Optional[FeatureFlagConfig] = None

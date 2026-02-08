"""
Tenant Management API Endpoints
Phase 4C: Task 7.3 & 7.4 - Tenant Configuration & API Key Management

Handles tenant CRUD, API key management, and tenant configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


import secrets
import hashlib
import logging

from src.database import get_db
from src.auth.dependencies import (
    require_superuser,
    CurrentUser,
)
from src.models.tenant_models import Tenant, TenantAPIKey, TenantUser, TenantAuditLog
from src.models.transaction_models import Transaction, Alert, Case
from src.schemas.tenant_schemas import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantStats,
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyUpdate,
    APIKeyRotateResponse,
    TenantUserCreate,
    TenantUserUpdate,
    TenantUserResponse,
    TenantConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


# ============================================================================
# TENANT MANAGEMENT
# ============================================================================


@router.post("/", response_model=TenantResponse, status_code=201)
def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Create a new tenant.

    Requires admin privileges.
    """
    # Check if tenant_id already exists
    existing = db.query(Tenant).filter(Tenant.tenant_id == tenant.tenant_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tenant ID already exists")

    # Create tenant
    db_tenant = Tenant(
        **tenant.dict(),
        settings={},
        rate_limits={
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000,
        },
        feature_flags={
            "ml_auto_triage": True,
            "websocket_notifications": True,
            "graphql_api": False,
        },
    )

    db.add(db_tenant)
    db.flush()

    # Audit log
    audit = TenantAuditLog(
        tenant_id=db_tenant.id,
        action_type="tenant.created",
        actor_user_id=current_user.user_id,
        description=f"Tenant '{tenant.name}' created",
        details={"tenant_id": tenant.tenant_id},
    )
    db.add(audit)

    db.commit()
    db.refresh(db_tenant)

    logger.info(f"Created tenant: {tenant.tenant_id}")
    return db_tenant


@router.get("/", response_model=List[TenantResponse])
def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    tier: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    List all tenants.

    Requires admin privileges.
    """
    query = db.query(Tenant)

    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)

    if tier:
        query = query.filter(Tenant.tier == tier)

    query = query.filter(Tenant.deleted_at.is_(None))  # Exclude soft-deleted
    query = query.order_by(Tenant.created_at.desc())

    tenants = query.offset(skip).limit(limit).all()
    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Get a specific tenant by ID.
    """
    tenant = (
        db.query(Tenant).filter(Tenant.tenant_id == tenant_id, Tenant.deleted_at.is_(None)).first()
    )

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    update_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Update a tenant.

    Requires admin privileges for the tenant.
    """
    tenant = (
        db.query(Tenant).filter(Tenant.tenant_id == tenant_id, Tenant.deleted_at.is_(None)).first()
    )

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(tenant, field, value)

    tenant.updated_at = utc_now()

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="tenant.updated",
        actor_user_id=current_user.user_id,
        description=f"Tenant '{tenant.name}' updated",
        details={"changes": update_dict},
    )
    db.add(audit)

    db.commit()
    db.refresh(tenant)

    logger.info(f"Updated tenant: {tenant_id}")
    return tenant


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(
    tenant_id: str,
    hard_delete: bool = Query(False, description="Permanently delete (cannot be undone)"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Delete a tenant (soft delete by default).

    Requires super admin privileges.
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if hard_delete:
        # Hard delete (WARNING: Permanent!)
        db.delete(tenant)
        action = "tenant.hard_deleted"
    else:
        # Soft delete
        tenant.deleted_at = utc_now()
        tenant.is_active = False
        action = "tenant.soft_deleted"

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type=action,
        actor_user_id=current_user.user_id,
        description=f"Tenant '{tenant.name}' deleted (hard={hard_delete})",
    )
    db.add(audit)

    db.commit()
    logger.warning(f"Deleted tenant: {tenant_id} (hard={hard_delete})")


@router.get("/{tenant_id}/stats", response_model=TenantStats)
def get_tenant_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Get statistics for a tenant.
    """
    tenant = (
        db.query(Tenant).filter(Tenant.tenant_id == tenant_id, Tenant.is_active == True).first()
    )

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Count resources
    total_transactions = (
        db.query(func.count(Transaction.id)).filter(Transaction.tenant_id == tenant_id).scalar()
        or 0
    )

    total_alerts = db.query(func.count(Alert.id)).filter(Alert.tenant_id == tenant_id).scalar() or 0

    total_cases = db.query(func.count(Case.id)).filter(Case.tenant_id == tenant_id).scalar() or 0

    total_users = (
        db.query(func.count(TenantUser.id))
        .filter(TenantUser.tenant_id == tenant.id, TenantUser.is_active == True)
        .scalar()
        or 0
    )

    active_api_keys = (
        db.query(func.count(TenantAPIKey.id))
        .filter(
            TenantAPIKey.tenant_id == tenant.id,
            TenantAPIKey.is_active == True,
            TenantAPIKey.revoked_at.is_(None),
        )
        .scalar()
        or 0
    )

    # API calls today (from API key usage)
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_today = (
        db.query(func.sum(TenantAPIKey.usage_count))
        .filter(TenantAPIKey.tenant_id == tenant.id, TenantAPIKey.last_used_at >= today_start)
        .scalar()
        or 0
    )

    return TenantStats(
        tenant_id=tenant_id,
        total_transactions=total_transactions,
        total_alerts=total_alerts,
        total_cases=total_cases,
        total_users=total_users,
        active_api_keys=active_api_keys,
        api_calls_today=api_calls_today,
        storage_used_mb=0.0,  # TODO: Calculate actual storage
    )


@router.patch("/{tenant_id}/config", response_model=TenantResponse)
def update_tenant_config(
    tenant_id: str,
    config: TenantConfigUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Update tenant configuration (settings, rate limits, feature flags).
    """
    tenant = (
        db.query(Tenant).filter(Tenant.tenant_id == tenant_id, Tenant.is_active == True).first()
    )

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Update configuration
    if config.settings:
        tenant.settings = config.settings.dict()

    if config.rate_limits:
        tenant.rate_limits = config.rate_limits.dict()

    if config.feature_flags:
        tenant.feature_flags = config.feature_flags.dict()

    tenant.updated_at = utc_now()

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="tenant.config_updated",
        actor_user_id=current_user.user_id,
        description="Tenant configuration updated",
        details=config.dict(exclude_unset=True),
    )
    db.add(audit)

    db.commit()
    db.refresh(tenant)

    logger.info(f"Updated config for tenant: {tenant_id}")
    return tenant


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================


@router.post("/{tenant_id}/api-keys", response_model=APIKeyCreateResponse, status_code=201)
def create_api_key(
    tenant_id: str,
    api_key_data: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Generate a new API key for a tenant.

    **IMPORTANT:** The full API key is only shown once at creation.
    Save it securely - it cannot be retrieved later.
    """
    tenant = (
        db.query(Tenant).filter(Tenant.tenant_id == tenant_id, Tenant.is_active == True).first()
    )

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Generate API key
    # Format: yk_live_<tenant_id>_<random>
    random_part = secrets.token_hex(16)  # 32 characters
    api_key = f"yk_live_{tenant_id}_{random_part}"

    # Hash for storage (SHA-256)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:20]  # Store prefix for identification

    # Create API key record
    db_api_key = TenantAPIKey(
        tenant_id=tenant.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=api_key_data.name,
        description=api_key_data.description,
        scopes=api_key_data.scopes or [],
        expires_at=api_key_data.expires_at,
        created_by=current_user.user_id,
        is_active=True,
    )

    db.add(db_api_key)

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="api_key.created",
        actor_user_id=current_user.user_id,
        description=f"API key '{api_key_data.name}' created",
        details={"key_prefix": key_prefix, "scopes": api_key_data.scopes or []},
    )
    db.add(audit)

    db.commit()
    db.refresh(db_api_key)

    logger.info(f"Created API key for tenant {tenant_id}: {key_prefix}...")

    # Return response with full API key (only time it's shown)
    response = APIKeyCreateResponse(
        **db_api_key.__dict__, api_key=api_key  # Full key - only shown once!
    )

    return response


@router.get("/{tenant_id}/api-keys", response_model=List[APIKeyResponse])
def list_api_keys(
    tenant_id: str,
    include_revoked: bool = Query(False, description="Include revoked keys"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    List all API keys for a tenant.

    Does NOT return the actual API keys (only metadata).
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = db.query(TenantAPIKey).filter(TenantAPIKey.tenant_id == tenant.id)

    if not include_revoked:
        query = query.filter(TenantAPIKey.revoked_at.is_(None))

    api_keys = query.order_by(TenantAPIKey.created_at.desc()).all()

    return api_keys


@router.patch("/{tenant_id}/api-keys/{key_id}", response_model=APIKeyResponse)
def update_api_key(
    tenant_id: str,
    key_id: int,
    update_data: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Update an API key (name, scopes, status).
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    api_key = (
        db.query(TenantAPIKey)
        .filter(TenantAPIKey.id == key_id, TenantAPIKey.tenant_id == tenant.id)
        .first()
    )

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(api_key, field, value)

    api_key.updated_at = utc_now()

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="api_key.updated",
        actor_user_id=current_user.user_id,
        description=f"API key '{api_key.name}' updated",
        details={"key_prefix": api_key.key_prefix, "changes": update_dict},
    )
    db.add(audit)

    db.commit()
    db.refresh(api_key)

    return api_key


@router.delete("/{tenant_id}/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    tenant_id: str,
    key_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Revoke an API key (cannot be undone).
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    api_key = (
        db.query(TenantAPIKey)
        .filter(TenantAPIKey.id == key_id, TenantAPIKey.tenant_id == tenant.id)
        .first()
    )

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Revoke the key
    api_key.is_active = False
    api_key.revoked_at = utc_now()

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="api_key.revoked",
        actor_user_id=current_user.user_id,
        description=f"API key '{api_key.name}' revoked",
        details={"key_prefix": api_key.key_prefix},
    )
    db.add(audit)

    db.commit()

    logger.warning(f"Revoked API key for tenant {tenant_id}: {api_key.key_prefix}...")


@router.post("/{tenant_id}/api-keys/{key_id}/rotate", response_model=APIKeyRotateResponse)
def rotate_api_key(
    tenant_id: str,
    key_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Rotate an API key (revoke old, create new).

    Returns the new API key - save it securely!
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    old_key = (
        db.query(TenantAPIKey)
        .filter(TenantAPIKey.id == key_id, TenantAPIKey.tenant_id == tenant.id)
        .first()
    )

    if not old_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Revoke old key
    old_key.is_active = False
    old_key.revoked_at = utc_now()

    # Create new key with same properties
    random_part = secrets.token_hex(16)
    new_api_key = f"yk_live_{tenant_id}_{random_part}"
    new_key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()
    new_key_prefix = new_api_key[:20]

    db_new_key = TenantAPIKey(
        tenant_id=tenant.id,
        key_hash=new_key_hash,
        key_prefix=new_key_prefix,
        name=f"{old_key.name} (rotated)",
        description=old_key.description,
        scopes=old_key.scopes,
        expires_at=old_key.expires_at,
        created_by=current_user.user_id,
        is_active=True,
    )

    db.add(db_new_key)

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="api_key.rotated",
        actor_user_id=current_user.user_id,
        description=f"API key '{old_key.name}' rotated",
        details={"old_key_prefix": old_key.key_prefix, "new_key_prefix": new_key_prefix},
    )
    db.add(audit)

    db.commit()
    db.refresh(db_new_key)

    logger.info(f"Rotated API key for tenant {tenant_id}")

    return APIKeyRotateResponse(
        old_key_id=old_key.id,
        new_key=APIKeyCreateResponse(**db_new_key.__dict__, api_key=new_api_key),
        message="API key rotated successfully. Old key is revoked.",
    )


# ============================================================================
# TENANT USERS
# ============================================================================


@router.post("/{tenant_id}/users", response_model=TenantUserResponse, status_code=201)
def add_user_to_tenant(
    tenant_id: str,
    user_data: TenantUserCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Add a user to a tenant with a specific role.
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if user already exists for this tenant
    existing = (
        db.query(TenantUser)
        .filter(TenantUser.tenant_id == tenant.id, TenantUser.user_id == user_data.user_id)
        .first()
    )

    if existing:
        raise HTTPException(status_code=409, detail="User already exists in this tenant")

    # Create tenant user
    db_user = TenantUser(tenant_id=tenant.id, **user_data.dict())

    db.add(db_user)

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="tenant_user.added",
        actor_user_id=current_user.user_id,
        description=f"User '{user_data.user_id}' added with role '{user_data.role}'",
        details={"user_id": user_data.user_id, "role": user_data.role},
    )
    db.add(audit)

    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("/{tenant_id}/users", response_model=List[TenantUserResponse])
def list_tenant_users(
    tenant_id: str,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    List all users in a tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = db.query(TenantUser).filter(TenantUser.tenant_id == tenant.id)

    if is_active is not None:
        query = query.filter(TenantUser.is_active == is_active)

    users = query.all()
    return users


@router.delete("/{tenant_id}/users/{user_id}", status_code=204)
def remove_user_from_tenant(
    tenant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_superuser()),
):
    """
    Remove a user from a tenant.
    """
    tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant_user = (
        db.query(TenantUser)
        .filter(TenantUser.tenant_id == tenant.id, TenantUser.user_id == user_id)
        .first()
    )

    if not tenant_user:
        raise HTTPException(status_code=404, detail="User not found in tenant")

    db.delete(tenant_user)

    # Audit log
    audit = TenantAuditLog(
        tenant_id=tenant.id,
        action_type="tenant_user.removed",
        actor_user_id=current_user.user_id,
        description=f"User '{user_id}' removed from tenant",
    )
    db.add(audit)

    db.commit()

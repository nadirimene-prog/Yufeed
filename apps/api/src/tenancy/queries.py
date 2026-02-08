"""
Tenant-Aware Queries
Phase 4C: Task 7.2 - Row-Level Security

Utilities for automatic tenant filtering in database queries.
"""

import logging
from typing import Type, TypeVar, Optional
from sqlalchemy.orm import Session, Query
from fastapi import HTTPException

from src.tenancy.context import get_current_tenant

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_tenant_filtered_query(model: Type[T], db: Session) -> Query:
    """
    Get a SQLAlchemy query automatically filtered by current tenant.

    Usage:
        query = get_tenant_filtered_query(Alert, db)
        alerts = query.filter(Alert.status == 'pending').all()

    Args:
        model: SQLAlchemy model class
        db: Database session

    Returns:
        Query object filtered by tenant_id

    Raises:
        HTTPException: If no tenant context is set
    """
    tenant_id = get_current_tenant()

    if not tenant_id:
        logger.error(f"No tenant context set for query on {model.__name__}")
        raise HTTPException(status_code=403, detail="No tenant context available")

    # Check if model has tenant_id attribute
    if not hasattr(model, "tenant_id"):
        logger.warning(f"Model {model.__name__} does not have tenant_id field")
        return db.query(model)

    # Return query filtered by tenant
    return db.query(model).filter(model.tenant_id == tenant_id)


def require_tenant() -> str:
    """
    Require tenant context and return tenant ID.

    Usage:
        @router.get("/alerts")
        def get_alerts(tenant_id: str = Depends(require_tenant)):
            # tenant_id is guaranteed to be set
            pass

    Returns:
        Current tenant ID

    Raises:
        HTTPException: If no tenant context is set
    """
    tenant_id = get_current_tenant()

    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant context available")

    return tenant_id


def ensure_tenant_match(entity, tenant_id: str) -> None:
    """
    Ensure an entity belongs to the specified tenant.

    Args:
        entity: Database model instance
        tenant_id: Expected tenant ID

    Raises:
        HTTPException: If entity belongs to different tenant
    """
    if not hasattr(entity, "tenant_id"):
        return

    if entity.tenant_id != tenant_id:
        logger.warning(
            f"Tenant mismatch: entity belongs to {entity.tenant_id}, "
            f"but current tenant is {tenant_id}"
        )
        raise HTTPException(
            status_code=403, detail="Access denied: entity belongs to different tenant"
        )


def set_tenant_on_create(entity, tenant_id: Optional[str] = None) -> None:
    """
    Set tenant_id on a new entity before creation.

    Args:
        entity: Database model instance
        tenant_id: Optional tenant ID (uses current context if not provided)

    Raises:
        HTTPException: If no tenant context and tenant_id not provided
    """
    if not hasattr(entity, "tenant_id"):
        return

    if tenant_id is None:
        tenant_id = get_current_tenant()

    if not tenant_id:
        raise HTTPException(
            status_code=403, detail="No tenant context available for entity creation"
        )

    entity.tenant_id = tenant_id
    logger.debug(f"Set tenant_id={tenant_id} on {type(entity).__name__}")


# Decorator for tenant-aware endpoints
def tenant_required(func):
    """
    Decorator to ensure tenant context exists for an endpoint.

    Usage:
        @router.get("/alerts")
        @tenant_required
        def get_alerts(db: Session = Depends(get_db)):
            # Tenant context is guaranteed to exist
            query = get_tenant_filtered_query(Alert, db)
            return query.all()
    """
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        tenant_id = get_current_tenant()
        if not tenant_id:
            raise HTTPException(status_code=403, detail="No tenant context available")
        return await func(*args, **kwargs)

    return wrapper

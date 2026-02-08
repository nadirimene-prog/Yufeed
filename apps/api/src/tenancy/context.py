"""
Tenant Context Management
Phase 4C: Task 7.2 - Multi-Tenancy Context

Manages tenant context using Python contextvars for thread-safe tenant isolation.
"""

from contextvars import ContextVar
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Thread-safe tenant context variable
tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_context", default=None)


def get_current_tenant() -> Optional[str]:
    """
    Get the current tenant ID from context.

    Returns:
        Current tenant ID or None if not set
    """
    return tenant_context.get()


def set_current_tenant(tenant_id: str) -> None:
    """
    Set the current tenant ID in context.

    Args:
        tenant_id: Tenant identifier to set

    Raises:
        ValueError: If tenant_id is None or empty
    """
    if not tenant_id:
        raise ValueError("tenant_id cannot be None or empty")

    tenant_context.set(tenant_id)
    logger.debug(f"Tenant context set to: {tenant_id}")


def clear_current_tenant() -> None:
    """
    Clear the current tenant context.
    """
    tenant_context.set(None)
    logger.debug("Tenant context cleared")


class TenantContext:
    """
    Context manager for tenant operations.

    Usage:
        with TenantContext("acme_corp"):
            # All queries in this block are scoped to acme_corp
            alerts = db.query(Alert).all()
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.token = None

    def __enter__(self):
        """Enter tenant context."""
        self.token = tenant_context.set(self.tenant_id)
        logger.debug(f"Entered tenant context: {self.tenant_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit tenant context."""
        if self.token:
            tenant_context.reset(self.token)
        logger.debug(f"Exited tenant context: {self.tenant_id}")
        return False

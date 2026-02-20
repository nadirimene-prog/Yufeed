"""Shared policy access helpers for API modules."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser
from src.models.compliance_workflow import PolicyDocument


def effective_tenant_id(
    current_user: Optional[CurrentUser],
    requested_tenant_id: Optional[str] = None,
) -> Optional[str]:
    """Resolve tenant context using explicit request value first."""
    if isinstance(requested_tenant_id, str) and requested_tenant_id.strip():
        return requested_tenant_id.strip()
    if current_user is None:
        return None
    return current_user.tenant_id


def is_policy_visible_to_tenant(policy: PolicyDocument, tenant_id: Optional[str]) -> bool:
    """A policy is visible when shared (master) or owned by the same tenant."""
    if tenant_id is None:
        return True
    return policy.tenant_id in (None, tenant_id)


def resolve_policy(db: Session, policy_identifier: str | int) -> Optional[PolicyDocument]:
    """Resolve policy by business identifier first, then by integer primary key."""
    key = str(policy_identifier).strip()
    if not key:
        return None

    policy = db.query(PolicyDocument).filter(PolicyDocument.policy_id == key).first()
    if policy:
        return policy

    if key.isdigit():
        return db.query(PolicyDocument).filter(PolicyDocument.id == int(key)).first()

    return None


def enforce_policy_visibility(
    policy: PolicyDocument,
    current_user: CurrentUser,
    *,
    requested_tenant_id: Optional[str] = None,
) -> None:
    """Raise 404 when policy is not visible in the effective tenant context."""
    tenant_id = effective_tenant_id(current_user, requested_tenant_id)
    if not is_policy_visible_to_tenant(policy, tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")


def enforce_policy_editable(
    policy: PolicyDocument,
    current_user: CurrentUser,
    *,
    requested_tenant_id: Optional[str] = None,
) -> None:
    """
    Enforce edition rights.

    Master policies are editable by superusers only.
    """
    enforce_policy_visibility(policy, current_user, requested_tenant_id=requested_tenant_id)
    if policy.is_master and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Master policies are editable by superusers only",
        )


def enforce_policy_linkable(
    policy: PolicyDocument,
    current_user: CurrentUser,
    *,
    requested_tenant_id: Optional[str] = None,
) -> None:
    """
    Enforce linking rights (obligation <-> policy).

    Master policies can be linked by compliance roles, while edits remain restricted.
    """
    enforce_policy_visibility(policy, current_user, requested_tenant_id=requested_tenant_id)
    if current_user.is_superuser:
        return

    if policy.is_master:
        if current_user.role not in {"admin", "compliance", "aml_officer"}:
            raise HTTPException(
                status_code=403,
                detail="Master policies can only be linked by compliance roles",
            )

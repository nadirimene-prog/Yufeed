"""Workspace helper endpoints used by assignment UIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dashboard_work_queue import _list_workspace_users
from src.auth.dependencies import CurrentUser, require_any_role
from src.database import get_db
from src.schemas.dashboard_v3 import WorkspaceUser

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.get("/users", response_model=list[WorkspaceUser])
def get_workspace_users(
    tenant_id: str | None = Query(None),
    is_active: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Return assignable tenant users for workspace-level analyst pickers."""
    return _list_workspace_users(
        tenant_id=tenant_id,
        is_active=is_active,
        db=db,
        current_user=current_user,
    )

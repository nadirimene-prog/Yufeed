"""Server-backed saved views and UI preferences for AMLCO dashboard v3."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser, require_any_role
from src.database import get_db
from src.models.tenant_models import Tenant, TenantUser
from src.models.user import User
from src.schemas.dashboard_v3 import (
    DashboardLayoutPreferences,
    DashboardPreferencesResponse,
    DashboardPreferencesUpdateRequest,
    DashboardSavedViewCreateRequest,
    DashboardSavedViewRecord,
    DashboardSavedViewsResponse,
    DashboardSavedViewUpdateRequest,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-preferences"])

_DASHBOARD_PREFS_KEY = "dashboard_v3"
_USER_PRIVATE_VIEWS_KEY = "saved_views_private"
_TENANT_TEAM_VIEWS_KEY = "saved_views_team"
_USER_PREFERENCES_KEY = "preferences"
_TEAM_MANAGE_ROLES = {"admin", "compliance", "manager", "qa_audit"}
_DASHBOARD_ALLOWED_ROLES = [
    "admin",
    "compliance",
    "auditor",
    "user",
    "viewer",
    "analyst",
    "reviewer",
    "manager",
    "qa_audit",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_user_record(db: Session, current_user: CurrentUser) -> User:
    user = db.query(User).filter(User.email == current_user.email).first()
    if user:
        return user
    if current_user.user_id and str(current_user.user_id).isdigit():
        user = db.query(User).filter(User.id == int(current_user.user_id)).first()
        if user:
            return user
    raise HTTPException(status_code=404, detail="User record not found")


def _resolve_tenant_record(
    db: Session,
    current_user: CurrentUser,
    *,
    required: bool = False,
) -> Tenant | None:
    if not current_user.tenant_id:
        if required:
            raise HTTPException(status_code=400, detail="Tenant context required")
        return None
    tenant = db.query(Tenant).filter(Tenant.tenant_id == current_user.tenant_id).first()
    if tenant is None and required:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _ensure_tenant_membership(db: Session, tenant: Tenant, current_user: CurrentUser) -> TenantUser:
    membership = (
        db.query(TenantUser)
        .filter(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == str(current_user.user_id),
            TenantUser.is_active.is_(True),
        )
        .first()
    )
    if membership is None and current_user.is_superuser:
        # Superusers may manage tenant dashboard views even if no explicit membership exists.
        return TenantUser(tenant_id=tenant.id, user_id=str(current_user.user_id), role="admin")
    if membership is None:
        raise HTTPException(status_code=403, detail="Tenant membership required")
    return membership


def _user_dashboard_blob(user: User) -> dict[str, Any]:
    root = deepcopy(user.preferences or {})
    dashboard = root.get(_DASHBOARD_PREFS_KEY)
    if not isinstance(dashboard, dict):
        dashboard = {}
    root[_DASHBOARD_PREFS_KEY] = dashboard
    return root


def _tenant_dashboard_blob(tenant: Tenant) -> dict[str, Any]:
    root = deepcopy(tenant.settings or {})
    dashboard = root.get(_DASHBOARD_PREFS_KEY)
    if not isinstance(dashboard, dict):
        dashboard = {}
    root[_DASHBOARD_PREFS_KEY] = dashboard
    return root


def _parse_saved_view_records(items: Any) -> list[DashboardSavedViewRecord]:
    if not isinstance(items, list):
        return []
    parsed: list[DashboardSavedViewRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            parsed.append(DashboardSavedViewRecord.model_validate(item))
        except Exception:
            continue
    return parsed


def _serialize_saved_view_records(records: list[DashboardSavedViewRecord]) -> list[dict[str, Any]]:
    return [record.model_dump(mode="json") for record in records]


def _read_private_views(user: User) -> list[DashboardSavedViewRecord]:
    dashboard = (user.preferences or {}).get(_DASHBOARD_PREFS_KEY)
    if not isinstance(dashboard, dict):
        return []
    return _parse_saved_view_records(dashboard.get(_USER_PRIVATE_VIEWS_KEY))


def _write_private_views(user: User, records: list[DashboardSavedViewRecord]) -> None:
    root = _user_dashboard_blob(user)
    dashboard = root[_DASHBOARD_PREFS_KEY]
    dashboard[_USER_PRIVATE_VIEWS_KEY] = _serialize_saved_view_records(records)
    user.preferences = root


def _read_team_views(tenant: Tenant | None) -> list[DashboardSavedViewRecord]:
    if tenant is None:
        return []
    dashboard = (tenant.settings or {}).get(_DASHBOARD_PREFS_KEY)
    if not isinstance(dashboard, dict):
        return []
    return _parse_saved_view_records(dashboard.get(_TENANT_TEAM_VIEWS_KEY))


def _write_team_views(tenant: Tenant, records: list[DashboardSavedViewRecord]) -> None:
    root = _tenant_dashboard_blob(tenant)
    dashboard = root[_DASHBOARD_PREFS_KEY]
    dashboard[_TENANT_TEAM_VIEWS_KEY] = _serialize_saved_view_records(records)
    tenant.settings = root


def _read_preferences(user: User) -> DashboardPreferencesResponse:
    dashboard = (user.preferences or {}).get(_DASHBOARD_PREFS_KEY)
    if not isinstance(dashboard, dict):
        return DashboardPreferencesResponse()
    raw = dashboard.get(_USER_PREFERENCES_KEY)
    if not isinstance(raw, dict):
        return DashboardPreferencesResponse()
    try:
        return DashboardPreferencesResponse.model_validate(raw)
    except Exception:
        return DashboardPreferencesResponse()


def _write_preferences(user: User, prefs: DashboardPreferencesResponse) -> None:
    root = _user_dashboard_blob(user)
    dashboard = root[_DASHBOARD_PREFS_KEY]
    dashboard[_USER_PREFERENCES_KEY] = prefs.model_dump(mode="json")
    user.preferences = root


def _clear_role_default_for_scope(
    records: list[DashboardSavedViewRecord],
    *,
    role: str | None,
    except_id: str | None = None,
) -> list[DashboardSavedViewRecord]:
    if not role:
        return records
    normalized: list[DashboardSavedViewRecord] = []
    for record in records:
        if record.id != except_id and record.is_default_for_role and record.role == role:
            normalized.append(record.model_copy(update={"is_default_for_role": False}))
        else:
            normalized.append(record)
    return normalized


def _coerce_record_update(
    current: DashboardSavedViewRecord,
    payload: DashboardSavedViewUpdateRequest,
    *,
    actor_user_id: str,
    now: datetime,
) -> DashboardSavedViewRecord:
    updates: dict[str, Any] = {"updated_at": now, "updated_by_user_id": actor_user_id}
    fields_set = payload.model_fields_set
    if "name" in fields_set:
        updates["name"] = payload.name
    if "scope" in fields_set and payload.scope is not None:
        updates["scope"] = payload.scope
    if "is_default_for_role" in fields_set and payload.is_default_for_role is not None:
        updates["is_default_for_role"] = payload.is_default_for_role
    if "role" in fields_set:
        updates["role"] = payload.role
    if "filters" in fields_set and payload.filters is not None:
        updates["filters"] = payload.filters
    if "layout_prefs" in fields_set:
        updates["layout_prefs"] = payload.layout_prefs
    return current.model_copy(update=updates)


def _resolve_visible_default_view_id(
    views: list[DashboardSavedViewRecord],
    *,
    current_role: str | None,
) -> str | None:
    if not current_role:
        return None
    candidates = [
        record for record in views if record.is_default_for_role and record.role == current_role
    ]
    if not candidates:
        return None
    # Prefer private defaults over team defaults, then newest update.
    candidates.sort(
        key=lambda record: (
            0 if record.scope == "private" else 1,
            -record.updated_at.timestamp(),
        )
    )
    return candidates[0].id


@router.get("/views", response_model=DashboardSavedViewsResponse)
def list_dashboard_saved_views(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_DASHBOARD_ALLOWED_ROLES)),
):
    user = _resolve_user_record(db, current_user)
    tenant = _resolve_tenant_record(db, current_user, required=False)
    if tenant is not None:
        _ensure_tenant_membership(db, tenant, current_user)

    private_views = _read_private_views(user)
    team_views = _read_team_views(tenant)
    visible = [*private_views, *team_views]
    visible.sort(key=lambda item: item.updated_at, reverse=True)

    return DashboardSavedViewsResponse(
        items=visible,
        resolved_default_view_id=_resolve_visible_default_view_id(
            visible, current_role=current_user.role
        ),
    )


@router.post("/views", response_model=DashboardSavedViewRecord, status_code=status.HTTP_201_CREATED)
def create_dashboard_saved_view(
    payload: DashboardSavedViewCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_DASHBOARD_ALLOWED_ROLES)),
):
    user = _resolve_user_record(db, current_user)
    now = _utc_now()
    team_id: str | None = None

    record = DashboardSavedViewRecord(
        id=f"dsv_{uuid.uuid4().hex}",
        name=payload.name.strip(),
        scope=payload.scope,
        owner_user_id=str(current_user.user_id),
        team_id=None,
        is_default_for_role=bool(payload.is_default_for_role and payload.role),
        role=payload.role if payload.is_default_for_role else payload.role,
        filters=payload.filters,
        layout_prefs=payload.layout_prefs,
        created_at=now,
        updated_at=now,
        updated_by_user_id=str(current_user.user_id),
    )

    if record.scope == "team":
        tenant = _resolve_tenant_record(db, current_user, required=True)
        membership = _ensure_tenant_membership(db, tenant, current_user)
        if record.is_default_for_role and membership.role not in _TEAM_MANAGE_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Manager/compliance/admin role required to set team role defaults",
            )
        team_id = current_user.tenant_id
        record = record.model_copy(update={"team_id": team_id})
        team_views = _read_team_views(tenant)
        if record.is_default_for_role and record.role:
            team_views = _clear_role_default_for_scope(
                team_views, role=record.role, except_id=record.id
            )
        team_views.append(record)
        _write_team_views(tenant, team_views)
    else:
        private_views = _read_private_views(user)
        if record.is_default_for_role and record.role:
            private_views = _clear_role_default_for_scope(
                private_views, role=record.role, except_id=record.id
            )
        private_views.append(record)
        _write_private_views(user, private_views)

    db.commit()
    return record


@router.patch("/views/{view_id}", response_model=DashboardSavedViewRecord)
def update_dashboard_saved_view(
    view_id: str,
    payload: DashboardSavedViewUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_DASHBOARD_ALLOWED_ROLES)),
):
    user = _resolve_user_record(db, current_user)
    tenant = _resolve_tenant_record(db, current_user, required=False)
    membership = _ensure_tenant_membership(db, tenant, current_user) if tenant else None
    private_views = _read_private_views(user)
    team_views = _read_team_views(tenant)

    source_scope: str | None = None
    source_index: int | None = None
    current_record: DashboardSavedViewRecord | None = None

    for index, record in enumerate(private_views):
        if record.id == view_id:
            source_scope = "private"
            source_index = index
            current_record = record
            break
    if current_record is None:
        for index, record in enumerate(team_views):
            if record.id == view_id:
                source_scope = "team"
                source_index = index
                current_record = record
                break

    if current_record is None or source_scope is None or source_index is None:
        raise HTTPException(status_code=404, detail="Saved view not found")

    actor_user_id = str(current_user.user_id)
    is_owner = current_record.owner_user_id == actor_user_id
    if source_scope == "team" and not is_owner and current_user.role not in _TEAM_MANAGE_ROLES:
        raise HTTPException(
            status_code=403, detail="Only owner or manager/compliance/admin can edit team views"
        )
    if source_scope == "private" and not is_owner:
        raise HTTPException(status_code=403, detail="Only owner can edit private saved views")

    now = _utc_now()
    next_record = _coerce_record_update(
        current_record, payload, actor_user_id=actor_user_id, now=now
    )
    target_scope = next_record.scope

    if target_scope == "team":
        if tenant is None:
            tenant = _resolve_tenant_record(db, current_user, required=True)
        if membership is None:
            membership = _ensure_tenant_membership(db, tenant, current_user)
        if next_record.is_default_for_role and membership.role not in _TEAM_MANAGE_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Manager/compliance/admin role required to set team role defaults",
            )
        next_record = next_record.model_copy(update={"team_id": current_user.tenant_id})
    else:
        next_record = next_record.model_copy(update={"team_id": None})

    if source_scope == "private":
        private_views.pop(source_index)
    else:
        team_views.pop(source_index)

    if target_scope == "private":
        if next_record.is_default_for_role and next_record.role:
            private_views = _clear_role_default_for_scope(
                private_views, role=next_record.role, except_id=next_record.id
            )
        private_views.append(next_record)
    else:
        if next_record.is_default_for_role and next_record.role:
            team_views = _clear_role_default_for_scope(
                team_views, role=next_record.role, except_id=next_record.id
            )
        team_views.append(next_record)

    _write_private_views(user, private_views)
    if tenant is not None:
        _write_team_views(tenant, team_views)
    db.commit()
    return next_record


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard_saved_view(
    view_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_DASHBOARD_ALLOWED_ROLES)),
):
    user = _resolve_user_record(db, current_user)
    tenant = _resolve_tenant_record(db, current_user, required=False)
    membership = _ensure_tenant_membership(db, tenant, current_user) if tenant else None

    private_views = _read_private_views(user)
    for index, record in enumerate(private_views):
        if record.id == view_id:
            if record.owner_user_id != str(current_user.user_id):
                raise HTTPException(
                    status_code=403, detail="Only owner can delete private saved views"
                )
            private_views.pop(index)
            _write_private_views(user, private_views)
            db.commit()
            return None

    if tenant is not None:
        team_views = _read_team_views(tenant)
        for index, record in enumerate(team_views):
            if record.id == view_id:
                is_owner = record.owner_user_id == str(current_user.user_id)
                if not is_owner and (
                    membership is None or membership.role not in _TEAM_MANAGE_ROLES
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="Only owner or manager/compliance/admin can delete team views",
                    )
                team_views.pop(index)
                _write_team_views(tenant, team_views)
                db.commit()
                return None

    raise HTTPException(status_code=404, detail="Saved view not found")


@router.get("/preferences", response_model=DashboardPreferencesResponse)
def get_dashboard_preferences(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_DASHBOARD_ALLOWED_ROLES)),
):
    user = _resolve_user_record(db, current_user)
    prefs = _read_preferences(user)
    return prefs


@router.patch("/preferences", response_model=DashboardPreferencesResponse)
def update_dashboard_preferences(
    payload: DashboardPreferencesUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_DASHBOARD_ALLOWED_ROLES)),
):
    user = _resolve_user_record(db, current_user)
    current = _read_preferences(user)
    fields_set = payload.model_fields_set

    layout_prefs = current.layout_prefs
    if "layout_prefs" in fields_set and payload.layout_prefs is not None:
        layout_values = current.layout_prefs.model_dump()
        for key, value in payload.layout_prefs.model_dump().items():
            if value is not None:
                layout_values[key] = value
        layout_prefs = DashboardLayoutPreferences.model_validate(layout_values)

    default_saved_view_id = current.default_saved_view_id
    if "default_saved_view_id" in fields_set:
        default_saved_view_id = payload.default_saved_view_id
        if default_saved_view_id:
            tenant = _resolve_tenant_record(db, current_user, required=False)
            if tenant is not None:
                _ensure_tenant_membership(db, tenant, current_user)
            visible_ids = {
                view.id for view in [*_read_private_views(user), *_read_team_views(tenant)]
            }
            if default_saved_view_id not in visible_ids:
                raise HTTPException(status_code=400, detail="default_saved_view_id is not visible")

    updated = DashboardPreferencesResponse(
        layout_prefs=layout_prefs,
        default_saved_view_id=default_saved_view_id,
        updated_at=_utc_now(),
    )
    _write_preferences(user, updated)
    db.commit()
    return updated

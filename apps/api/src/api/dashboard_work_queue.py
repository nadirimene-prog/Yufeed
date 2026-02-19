"""AMLCO command center work-queue and work-item workflow APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from src.auth.dependencies import CurrentUser, require_any_role
from src.config import settings
from src.database import get_db
from src.models.case_decision import CaseDecision
from src.models.tenant_models import Tenant, TenantUser
from src.models.transaction_models import Alert, Case, Transaction
from src.schemas.dashboard_v3 import (
    ActionHistoryItem,
    AiRecommendation,
    DashboardWorkQueueItem,
    DashboardWorkQueueResponse,
    EvidenceChecklistItem,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewRequirement,
    WorkItemDraftUpdateRequest,
    WorkItemDraftUpdateResponse,
    WorkItemActionRequest,
    WorkItemActionResponse,
    WorkItemDetailResponse,
    WorkItemKind,
    WorkspaceUser,
    WorkItemTimelineEvent,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard-work-queue"])

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
SLA_HOURS = {"critical": 2, "high": 8, "medium": 24, "low": 48}
HIGH_RISK_JURISDICTIONS = {"IR", "KP", "SY", "AF", "MM", "RU"}
REVIEW_TYPOLOGIES = {"sanctions", "terrorist_financing", "structuring_high_value"}


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _tenant_filter(query, model, current_user: CurrentUser):
    if current_user.tenant_id and hasattr(model, "tenant_id"):
        return query.filter(model.tenant_id == current_user.tenant_id)
    return query


def _severity_from_case_priority(priority: str | None) -> str:
    value = (priority or "medium").lower()
    if value in {"critical", "high", "medium", "low"}:
        return value
    if value in {"p1", "urgent"}:
        return "critical"
    if value in {"p2"}:
        return "high"
    return "medium"


def _sla_due_at(created_at: datetime | None, severity: str, now: datetime) -> datetime | None:
    normalized = _as_utc(created_at)
    if not normalized:
        return None
    return normalized + timedelta(hours=SLA_HOURS.get(severity.lower(), SLA_HOURS["medium"]))


def _sla_status(sla_due_at: datetime | None, now: datetime) -> str:
    if not sla_due_at:
        return "none"
    if now >= sla_due_at:
        return "breached"
    if now + timedelta(hours=4) >= sla_due_at:
        return "warning"
    return "ok"


def _review_requirement(
    *,
    severity: str,
    risk_score: float,
    typology: str,
    jurisdiction: str,
    sar_required: bool,
) -> ReviewRequirement:
    reasons: list[str] = []
    if severity.lower() in {"high", "critical"}:
        reasons.append("severity_high_or_critical")
    if risk_score >= 80:
        reasons.append("risk_score_ge_80")
    if typology.lower() in REVIEW_TYPOLOGIES:
        reasons.append("typology_requires_secondary_review")
    if jurisdiction.upper() in HIGH_RISK_JURISDICTIONS:
        reasons.append("high_risk_jurisdiction")
    if sar_required:
        reasons.append("sar_required")
    return ReviewRequirement(required=bool(reasons), reasons=reasons)


def _age_minutes(started_at: datetime | None, now: datetime) -> int:
    normalized = _as_utc(started_at)
    if not normalized:
        return 0
    return max(0, int((now - normalized).total_seconds() // 60))


def _alert_queue_item(alert: Alert, now: datetime) -> DashboardWorkQueueItem:
    severity = (alert.severity or "medium").lower()
    transaction = alert.transaction
    jurisdiction = (
        transaction.country_code if transaction and transaction.country_code else "N/A"
    ).upper()
    risk_score = _to_float(alert.risk_score)
    sar_required = bool(severity in {"high", "critical"} and not bool(alert.sar_filed))
    review_requirement = _review_requirement(
        severity=severity,
        risk_score=risk_score,
        typology=alert.alert_type or "",
        jurisdiction=jurisdiction,
        sar_required=sar_required,
    )
    due_at = _sla_due_at(alert.created_at, severity, now)
    return DashboardWorkQueueItem(
        item_id=f"alert:{alert.id}",
        record_id=str(alert.id),
        kind="alert",
        ref_id=alert.alert_id,
        type_label="Alert",
        severity=severity,
        entity=alert.user_id or "unknown",
        typology=alert.alert_type or "unknown",
        jurisdiction=jurisdiction,
        age_minutes=_age_minutes(alert.created_at, now),
        sla_due_at=due_at,
        sla_status=_sla_status(due_at, now),
        owner=alert.assigned_to,
        next_action="Review and disposition",
        risk_score=risk_score,
        status=alert.status,
        sar_required=sar_required,
        review_requirement=review_requirement,
    )


def _case_queue_item(
    case: Case,
    now: datetime,
    transaction_lookup: dict[int, Transaction],
) -> DashboardWorkQueueItem:
    severity = _severity_from_case_priority(case.priority)
    transaction_ids = case.related_transaction_ids or []
    jurisdiction = "N/A"
    risk_score = 0.0
    for txn_id in transaction_ids:
        txn = transaction_lookup.get(txn_id)
        if not txn:
            continue
        risk_score = max(risk_score, _to_float(txn.risk_score))
        if txn.country_code:
            jurisdiction = txn.country_code.upper()
            break

    sar_required = (case.outcome or "").lower() == "sar_required"
    review_requirement = _review_requirement(
        severity=severity,
        risk_score=risk_score,
        typology=case.case_type or "investigation",
        jurisdiction=jurisdiction,
        sar_required=sar_required,
    )
    due_at = _sla_due_at(case.opened_at, severity, now)

    return DashboardWorkQueueItem(
        item_id=f"case:{case.id}",
        record_id=str(case.id),
        kind="case",
        ref_id=case.case_id,
        type_label="Case",
        severity=severity,
        entity=case.subject_id or "unknown",
        typology=case.case_type or "investigation",
        jurisdiction=jurisdiction,
        age_minutes=_age_minutes(case.opened_at, now),
        sla_due_at=due_at,
        sla_status=_sla_status(due_at, now),
        owner=case.assigned_to,
        next_action="Advance investigation",
        risk_score=risk_score,
        status=case.status,
        sar_required=sar_required,
        review_requirement=review_requirement,
    )


def _approval_queue_item(decision: CaseDecision, case_lookup: dict[int, Case], now: datetime):
    parent_case = case_lookup.get(decision.case_id)
    severity = _severity_from_case_priority(parent_case.priority if parent_case else "high")
    due_at = _sla_due_at(decision.submitted_at or decision.created_at, severity, now)
    return DashboardWorkQueueItem(
        item_id=f"approval:{decision.id}",
        record_id=str(decision.id),
        kind="approval",
        ref_id=f"DEC-{decision.id}",
        type_label="Approval",
        severity=severity,
        entity=(
            parent_case.subject_id
            if parent_case and parent_case.subject_id
            else decision.created_by
        ),
        typology="case_decision",
        jurisdiction="N/A",
        age_minutes=_age_minutes(decision.submitted_at or decision.created_at, now),
        sla_due_at=due_at,
        sla_status=_sla_status(due_at, now),
        owner=decision.approver_id,
        next_action="Approve or return",
        risk_score=0.0,
        status=decision.status,
        sar_required=decision.disposition == "sar_required",
        review_requirement=ReviewRequirement(required=True, reasons=["pending_approval"]),
    )


def _reg_task_queue_item(case: Case, now: datetime) -> DashboardWorkQueueItem:
    severity = "high"
    due_at = _sla_due_at(case.opened_at, severity, now)
    return DashboardWorkQueueItem(
        item_id=f"reg_task:{case.id}",
        record_id=str(case.id),
        kind="reg_task",
        ref_id=case.case_id,
        type_label="Reg Task",
        severity=severity,
        entity=case.subject_id or "unknown",
        typology="sar_deadline",
        jurisdiction="N/A",
        age_minutes=_age_minutes(case.opened_at, now),
        sla_due_at=due_at,
        sla_status=_sla_status(due_at, now),
        owner=case.assigned_to,
        next_action="Prepare SAR filing",
        risk_score=0.0,
        status=case.status,
        sar_required=True,
        review_requirement=ReviewRequirement(required=True, reasons=["sar_required"]),
    )


def _severity_rank(severity: str) -> int:
    return SEVERITY_RANK.get(severity.lower(), 0)


def _sort_items(items: list[DashboardWorkQueueItem]) -> list[DashboardWorkQueueItem]:
    def key(item: DashboardWorkQueueItem):
        return (
            1 if item.sla_status == "breached" else 0,
            _severity_rank(item.severity),
            item.risk_score,
            item.age_minutes,
        )

    return sorted(items, key=key, reverse=True)


def _resolve_alert(item_id: str, db: Session, current_user: CurrentUser) -> Alert:
    query = db.query(Alert).options(joinedload(Alert.transaction))
    query = _tenant_filter(query, Alert, current_user)
    if item_id.isdigit():
        alert = query.filter(Alert.id == int(item_id)).first()
    else:
        alert = query.filter(Alert.alert_id == item_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


def _resolve_case(item_id: str, db: Session, current_user: CurrentUser) -> Case:
    query = db.query(Case)
    query = _tenant_filter(query, Case, current_user)
    if item_id.isdigit():
        case = query.filter(Case.id == int(item_id)).first()
    else:
        case = query.filter(Case.case_id == item_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _resolve_approval(item_id: str, db: Session, current_user: CurrentUser) -> CaseDecision:
    if not item_id.isdigit():
        raise HTTPException(status_code=400, detail="Approval item id must be numeric")
    query = db.query(CaseDecision)
    query = _tenant_filter(query, CaseDecision, current_user)
    decision = query.filter(CaseDecision.id == int(item_id)).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Approval item not found")
    return decision


def _build_ai_recommendation(item: DashboardWorkQueueItem) -> AiRecommendation:
    confidence = 0.92 if item.severity in {"high", "critical"} else 0.74
    summary = (
        "Escalate immediately and preserve evidence trail."
        if item.severity == "critical"
        else "Proceed with analyst triage and collect supporting context."
    )
    rationale = [
        f"severity={item.severity}",
        f"risk_score={item.risk_score:.0f}",
        f"sla_status={item.sla_status}",
    ]
    if item.review_requirement.required:
        rationale.extend(item.review_requirement.reasons)

    return AiRecommendation(summary=summary, confidence=confidence, rationale=rationale)


@router.get("/work-queue", response_model=DashboardWorkQueueResponse)
def get_dashboard_work_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    queue: str = Query("all"),
    severity: str | None = Query(None),
    jurisdiction: str | None = Query(None),
    sla: str | None = Query(None),
    search: str | None = Query(None),
    saved_view: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Return AMLCO triage queue with filter, sort, and pagination support."""
    if not settings.DASHBOARD_AMLCO_V3_ENABLED:
        raise HTTPException(status_code=503, detail="Dashboard AMLCO v3 is currently disabled")

    now = utc_now()

    alert_query = (
        db.query(Alert)
        .options(joinedload(Alert.transaction))
        .filter(Alert.status.in_(["pending", "in_review"]))
    )
    alert_query = _tenant_filter(alert_query, Alert, current_user)
    alerts = alert_query.all()

    case_query = db.query(Case).filter(Case.status.in_(["open", "in_progress"]))
    case_query = _tenant_filter(case_query, Case, current_user)
    cases = case_query.all()

    decision_query = db.query(CaseDecision).filter(CaseDecision.status == "submitted")
    decision_query = _tenant_filter(decision_query, CaseDecision, current_user)
    decisions = decision_query.all()

    transaction_ids: set[int] = set()
    for case in cases:
        for txn_id in case.related_transaction_ids or []:
            if isinstance(txn_id, int):
                transaction_ids.add(txn_id)

    transaction_lookup: dict[int, Transaction] = {}
    if transaction_ids:
        txn_query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
        txn_query = _tenant_filter(txn_query, Transaction, current_user)
        transaction_lookup = {row.id: row for row in txn_query.all()}

    case_lookup = {case.id: case for case in cases}

    items: list[DashboardWorkQueueItem] = []
    items.extend(_alert_queue_item(alert, now) for alert in alerts)
    items.extend(_case_queue_item(case, now, transaction_lookup) for case in cases)
    items.extend(_approval_queue_item(decision, case_lookup, now) for decision in decisions)
    items.extend(
        _reg_task_queue_item(case, now)
        for case in cases
        if (case.outcome or "").lower() == "sar_required"
    )

    queue_value = (queue or "all").lower()
    if queue_value in {"alerts", "cases", "approvals", "reg_tasks"}:
        kind = "reg_task" if queue_value == "reg_tasks" else queue_value.rstrip("s")
        items = [item for item in items if item.kind == kind]

    if saved_view == "my_queue":
        items = [item for item in items if item.owner == current_user.user_id]
    elif saved_view == "escalations":
        items = [
            item
            for item in items
            if item.sla_status == "breached" or item.severity in {"high", "critical"}
        ]

    if severity and severity.lower() not in {"", "all"}:
        items = [item for item in items if item.severity.lower() == severity.lower()]

    if jurisdiction and jurisdiction.lower() not in {"", "all"}:
        target = jurisdiction.upper()
        items = [item for item in items if item.jurisdiction.upper() == target]

    if sla and sla.lower() not in {"", "all"}:
        items = [item for item in items if item.sla_status == sla.lower()]

    if search and search.strip():
        needle = search.strip().lower()
        items = [
            item
            for item in items
            if needle in item.entity.lower()
            or needle in item.ref_id.lower()
            or needle in item.typology.lower()
            or needle in item.jurisdiction.lower()
        ]

    items = _sort_items(items)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    return DashboardWorkQueueResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=page_items,
    )


@router.get("/workspace-users", response_model=list[WorkspaceUser])
def get_workspace_users(
    tenant_id: str | None = Query(None),
    is_active: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """
    List assignable users for the current workspace tenant.

    Non-superusers are restricted to their JWT tenant context.
    """
    return _list_workspace_users(
        tenant_id=tenant_id,
        is_active=is_active,
        db=db,
        current_user=current_user,
    )


def _list_workspace_users(
    tenant_id: str | None = None,
    is_active: bool = True,
    db: Session | None = None,
    current_user: CurrentUser | None = None,
):
    """
    List assignable users for the current workspace tenant.

    Non-superusers are restricted to their JWT tenant context.
    """
    if db is None or current_user is None:
        raise HTTPException(status_code=500, detail="Workspace user context missing")

    target_tenant = tenant_id or current_user.tenant_id
    if not target_tenant:
        raise HTTPException(
            status_code=400,
            detail="tenant_id is required when no tenant claim is present",
        )

    if not current_user.is_superuser and current_user.tenant_id != target_tenant:
        raise HTTPException(
            status_code=403,
            detail="Cannot access users outside current tenant",
        )

    tenant = (
        db.query(Tenant)
        .filter(Tenant.tenant_id == target_tenant, Tenant.deleted_at.is_(None))
        .first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = db.query(TenantUser).filter(TenantUser.tenant_id == tenant.id)
    query = query.filter(TenantUser.is_active.is_(is_active))
    users = query.order_by(TenantUser.user_id.asc()).all()
    return [
        WorkspaceUser(user_id=user.user_id, role=user.role, is_active=user.is_active)
        for user in users
    ]


@router.get("/work-items/{kind}/{item_id}", response_model=WorkItemDetailResponse)
def get_work_item_detail(
    kind: WorkItemKind,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Return detail payload for one work-item in the AMLCO workspace."""
    if not settings.DASHBOARD_AMLCO_V3_ENABLED:
        raise HTTPException(status_code=503, detail="Dashboard AMLCO v3 is currently disabled")

    now = utc_now()

    if kind == "alert":
        alert = _resolve_alert(item_id, db, current_user)
        queue_item = _alert_queue_item(alert, now)
        timeline = [
            WorkItemTimelineEvent(
                at=_as_utc(alert.created_at) or now,
                label="Alert created",
                detail=alert.alert_type,
            ),
            WorkItemTimelineEvent(
                at=_as_utc(alert.updated_at) or now,
                label="Last update",
                detail=alert.status,
            ),
        ]
        if alert.resolved_at:
            timeline.append(
                WorkItemTimelineEvent(
                    at=_as_utc(alert.resolved_at) or now,
                    label="Resolved",
                    detail=alert.resolution_status or "resolved",
                )
            )

        linked_transactions = [alert.transaction.transaction_id] if alert.transaction else []
        linked_entities = [alert.user_id] if alert.user_id else []
        evidence = [
            EvidenceChecklistItem(
                id="tx-context",
                label="Transaction context captured",
                completed=bool(alert.transaction_id),
            ),
            EvidenceChecklistItem(
                id="risk-evidence",
                label="Risk factors documented",
                completed=bool(alert.evidence or alert.matched_rules_data),
            ),
            EvidenceChecklistItem(
                id="resolution",
                label="Resolution narrative provided",
                completed=bool(alert.resolution_notes),
            ),
        ]
        actions = [
            ActionHistoryItem(
                at=_as_utc(alert.updated_at) or _as_utc(alert.created_at) or now,
                actor=alert.resolved_by or "system",
                action="alert_status_sync",
                notes=alert.status,
            )
        ]

        return WorkItemDetailResponse(
            work_item=queue_item,
            context_timeline=sorted(timeline, key=lambda item: item.at),
            linked_entities=linked_entities,
            linked_transactions=linked_transactions,
            ai_recommendation=_build_ai_recommendation(queue_item),
            narrative=alert.description or "",
            evidence_checklist=evidence,
            action_history=actions,
            review_requirement=queue_item.review_requirement,
            allowed_actions=["assign", "escalate", "mark_in_progress", "create_case", "close"],
        )

    if kind == "case":
        case = _resolve_case(item_id, db, current_user)
        transaction_lookup = {}
        transaction_ids = [
            txn_id for txn_id in case.related_transaction_ids or [] if isinstance(txn_id, int)
        ]
        if transaction_ids:
            query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
            query = _tenant_filter(query, Transaction, current_user)
            transaction_lookup = {row.id: row for row in query.all()}

        queue_item = _case_queue_item(case, now, transaction_lookup)

        timeline = [
            WorkItemTimelineEvent(
                at=_as_utc(case.opened_at) or now,
                label="Case opened",
                detail=case.case_type,
            ),
            WorkItemTimelineEvent(
                at=_as_utc(case.updated_at) or now,
                label="Last update",
                detail=case.status,
            ),
        ]
        if case.closed_at:
            timeline.append(
                WorkItemTimelineEvent(
                    at=_as_utc(case.closed_at) or now,
                    label="Case closed",
                    detail=case.outcome,
                )
            )

        linked_transactions = [
            transaction_lookup[txn_id].transaction_id
            for txn_id in transaction_ids
            if txn_id in transaction_lookup
        ]
        linked_entities = [entity for entity in (case.related_users or []) if entity]
        if case.subject_id:
            linked_entities.append(case.subject_id)

        evidence = [
            EvidenceChecklistItem(
                id="case-summary",
                label="Case summary present",
                completed=bool(case.summary or case.description),
            ),
            EvidenceChecklistItem(
                id="evidence", label="Evidence attached", completed=bool(case.evidence)
            ),
            EvidenceChecklistItem(
                id="decision", label="Outcome captured", completed=bool(case.outcome)
            ),
        ]
        actions = [
            ActionHistoryItem(
                at=_as_utc(case.updated_at) or _as_utc(case.created_at) or now,
                actor=case.assigned_to or "system",
                action="case_status_sync",
                notes=case.status,
            )
        ]

        return WorkItemDetailResponse(
            work_item=queue_item,
            context_timeline=sorted(timeline, key=lambda item: item.at),
            linked_entities=list(dict.fromkeys(linked_entities)),
            linked_transactions=linked_transactions,
            ai_recommendation=_build_ai_recommendation(queue_item),
            narrative=case.summary or case.description or "",
            evidence_checklist=evidence,
            action_history=actions,
            review_requirement=queue_item.review_requirement,
            allowed_actions=["assign", "escalate", "mark_in_progress", "close"],
        )

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        parent_case = _resolve_case(str(decision.case_id), db, current_user)
        queue_item = _approval_queue_item(decision, {parent_case.id: parent_case}, now)
        return WorkItemDetailResponse(
            work_item=queue_item,
            context_timeline=[
                WorkItemTimelineEvent(
                    at=_as_utc(decision.created_at) or now,
                    label="Decision draft created",
                    detail=decision.disposition,
                ),
                WorkItemTimelineEvent(
                    at=_as_utc(decision.submitted_at) or _as_utc(decision.updated_at) or now,
                    label="Submitted for approval",
                    detail=decision.status,
                ),
            ],
            linked_entities=[decision.created_by],
            linked_transactions=[],
            ai_recommendation=AiRecommendation(
                summary="Validate rationale and enforce 4-eyes policy before approval.",
                confidence=0.88,
                rationale=["approval_queue", "maker_checker_required"],
            ),
            narrative=decision.rationale or "",
            evidence_checklist=[
                EvidenceChecklistItem(
                    id="decision-rationale",
                    label="Decision rationale complete",
                    completed=bool(decision.rationale),
                ),
                EvidenceChecklistItem(
                    id="not-self-approved",
                    label="Approver differs from submitter",
                    completed=(decision.created_by != current_user.user_id),
                ),
            ],
            action_history=[],
            review_requirement=ReviewRequirement(required=True, reasons=["pending_approval"]),
            allowed_actions=["close"],
        )

    case = _resolve_case(item_id, db, current_user)
    queue_item = _reg_task_queue_item(case, now)
    return WorkItemDetailResponse(
        work_item=queue_item,
        context_timeline=[
            WorkItemTimelineEvent(
                at=_as_utc(case.opened_at) or now,
                label="Regulatory task created",
                detail="SAR filing window started",
            )
        ],
        linked_entities=[case.subject_id] if case.subject_id else [],
        linked_transactions=[],
        ai_recommendation=AiRecommendation(
            summary="Prepare SAR packet and route for compliance review.",
            confidence=0.84,
            rationale=["regulatory_deadline", "sar_required"],
        ),
        narrative=case.summary or case.description or "",
        evidence_checklist=[
            EvidenceChecklistItem(
                id="sar-template", label="SAR template initialized", completed=False
            ),
            EvidenceChecklistItem(
                id="evidence-pack", label="Evidence pack attached", completed=bool(case.evidence)
            ),
        ],
        action_history=[],
        review_requirement=queue_item.review_requirement,
        allowed_actions=["mark_in_progress", "close"],
    )


@router.patch("/work-items/{kind}/{item_id}", response_model=WorkItemDraftUpdateResponse)
def update_work_item_draft(
    kind: WorkItemKind,
    item_id: str,
    payload: WorkItemDraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Persist editable narrative/notes drafts for workspace items."""
    if not settings.DASHBOARD_AMLCO_V3_ENABLED:
        raise HTTPException(status_code=503, detail="Dashboard AMLCO v3 is currently disabled")

    now = utc_now()

    if kind == "alert":
        alert = _resolve_alert(item_id, db, current_user)
        if payload.narrative is not None:
            alert.description = payload.narrative
        if payload.notes is not None:
            alert.resolution_notes = payload.notes
        alert.updated_at = now
        db.commit()
        return WorkItemDraftUpdateResponse(
            success=True, message="Alert draft updated", updated_at=alert.updated_at or now
        )

    if kind in {"case", "reg_task"}:
        case = _resolve_case(item_id, db, current_user)
        if payload.narrative is not None:
            case.summary = payload.narrative
        if payload.notes is not None:
            case.outcome_notes = payload.notes
        case.updated_at = now
        db.commit()
        return WorkItemDraftUpdateResponse(
            success=True, message="Case draft updated", updated_at=case.updated_at or now
        )

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        if payload.narrative is not None:
            decision.rationale = payload.narrative
        if payload.notes is not None:
            decision.rejection_reason = payload.notes
        decision.updated_at = now
        db.commit()
        return WorkItemDraftUpdateResponse(
            success=True, message="Approval draft updated", updated_at=decision.updated_at or now
        )

    raise HTTPException(status_code=400, detail="Unsupported work item kind")


@router.post("/work-items/{kind}/{item_id}/actions", response_model=WorkItemActionResponse)
def perform_work_item_action(
    kind: WorkItemKind,
    item_id: str,
    payload: WorkItemActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Execute controlled actions from the command center workspace."""
    if not settings.DASHBOARD_AMLCO_V3_ENABLED:
        raise HTTPException(status_code=503, detail="Dashboard AMLCO v3 is currently disabled")

    now = utc_now()

    if kind == "alert":
        alert = _resolve_alert(item_id, db, current_user)

        if payload.action == "assign":
            if not payload.assignee:
                raise HTTPException(
                    status_code=400, detail="assignee is required for assign action"
                )
            alert.assigned_to = payload.assignee
            alert.status = "in_review"
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Alert assigned", updated_status=alert.status
            )

        if payload.action == "escalate":
            alert.priority = 1
            alert.status = "in_review"
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Alert escalated", updated_status=alert.status
            )

        if payload.action == "mark_in_progress":
            alert.status = "in_review"
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Alert moved to in review", updated_status=alert.status
            )

        if payload.action == "create_case":
            case_id = f"CASE-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            case = Case(
                tenant_id=alert.tenant_id,
                case_id=case_id,
                case_type="investigation",
                subject_type="user",
                subject_id=alert.user_id,
                status="open",
                priority="high" if alert.severity in {"high", "critical"} else "medium",
                assigned_to=current_user.user_id,
                title=f"Investigation for {alert.alert_id}",
                description=alert.description,
                related_alert_ids=[alert.id],
                related_transaction_ids=[alert.transaction_id] if alert.transaction_id else [],
                related_users=[alert.user_id] if alert.user_id else [],
                evidence=alert.evidence or {},
                opened_at=now,
            )
            db.add(case)
            alert.status = "in_review"
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Case created from alert",
                updated_status=alert.status,
                created_case_id=case.case_id,
            )

        if payload.action == "close":
            queue_item = _alert_queue_item(alert, now)
            if queue_item.review_requirement.required:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Close action requires reviewer approval",
                        "reasons": queue_item.review_requirement.reasons,
                    },
                )
            alert.status = "resolved"
            alert.resolution_status = "closed"
            alert.resolution_notes = payload.notes
            alert.resolved_by = current_user.user_id
            alert.resolved_at = now
            if payload.sar_required:
                alert.sar_filed = True
                alert.sar_filed_at = now
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Alert closed", updated_status=alert.status
            )

        raise HTTPException(status_code=400, detail="Unsupported action for alert")

    if kind in {"case", "reg_task"}:
        case = _resolve_case(item_id, db, current_user)

        if payload.action == "assign":
            if not payload.assignee:
                raise HTTPException(
                    status_code=400, detail="assignee is required for assign action"
                )
            case.assigned_to = payload.assignee
            case.status = "in_progress"
            case.updated_at = now
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Case assigned", updated_status=case.status
            )

        if payload.action == "escalate":
            case.priority = "high"
            case.status = "in_progress"
            case.updated_at = now
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Case escalated", updated_status=case.status
            )

        if payload.action == "mark_in_progress":
            case.status = "in_progress"
            case.updated_at = now
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Case in progress", updated_status=case.status
            )

        if payload.action == "close":
            transaction_lookup = {}
            transaction_ids = [
                txn_id for txn_id in case.related_transaction_ids or [] if isinstance(txn_id, int)
            ]
            if transaction_ids:
                query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
                query = _tenant_filter(query, Transaction, current_user)
                transaction_lookup = {row.id: row for row in query.all()}
            queue_item = _case_queue_item(case, now, transaction_lookup)
            if queue_item.review_requirement.required:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Close action requires reviewer approval",
                        "reasons": queue_item.review_requirement.reasons,
                    },
                )
            case.status = "closed"
            case.outcome = "sar_required" if payload.sar_required else "no_action"
            case.outcome_notes = payload.notes
            case.closed_at = now
            case.updated_at = now
            db.commit()
            return WorkItemActionResponse(
                success=True, message="Case closed", updated_status=case.status
            )

        if payload.action == "create_case":
            raise HTTPException(
                status_code=400, detail="create_case is only available for alert items"
            )

        raise HTTPException(status_code=400, detail="Unsupported action for case")

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        if payload.action != "close":
            raise HTTPException(
                status_code=400, detail="Only close action is supported for approval items"
            )
        if decision.created_by == current_user.user_id:
            raise HTTPException(
                status_code=409,
                detail="4-eyes violation: approver cannot be the same as submitter",
            )
        decision.status = "approved"
        decision.approver_id = current_user.user_id
        decision.approved_at = now
        db.commit()
        return WorkItemActionResponse(
            success=True, message="Approval completed", updated_status=decision.status
        )

    raise HTTPException(status_code=400, detail="Unsupported work item kind")


@router.post("/work-items/{kind}/{item_id}/review", response_model=ReviewActionResponse)
def review_work_item(
    kind: WorkItemKind,
    item_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Perform maker-checker review for close/approve decisions."""
    if not settings.DASHBOARD_AMLCO_V3_ENABLED:
        raise HTTPException(status_code=503, detail="Dashboard AMLCO v3 is currently disabled")

    now = utc_now()

    if payload.decision == "approve" and payload.submitted_by == current_user.user_id:
        raise HTTPException(
            status_code=409,
            detail="4-eyes violation: approver cannot be the same as submitter",
        )

    if kind == "alert":
        alert = _resolve_alert(item_id, db, current_user)
        if payload.decision == "approve":
            alert.status = "resolved"
            alert.resolution_status = "review_approved"
            alert.resolution_notes = payload.review_notes
            alert.resolved_by = current_user.user_id
            alert.resolved_at = now
            if payload.sar_required:
                alert.sar_filed = True
                alert.sar_filed_at = now
            db.commit()
            return ReviewActionResponse(
                success=True,
                review_status="approved",
                updated_status=alert.status,
                message="Alert closure approved",
            )

        alert.status = "in_review"
        alert.resolution_notes = payload.review_notes
        db.commit()
        return ReviewActionResponse(
            success=True,
            review_status="returned",
            updated_status=alert.status,
            message="Alert returned for additional investigation",
        )

    if kind in {"case", "reg_task"}:
        case = _resolve_case(item_id, db, current_user)
        if payload.decision == "approve":
            case.status = "closed"
            case.closed_at = now
            case.outcome = "sar_required" if payload.sar_required else "no_action"
            case.outcome_notes = payload.review_notes
            case.updated_at = now
            db.commit()
            return ReviewActionResponse(
                success=True,
                review_status="approved",
                updated_status=case.status,
                message="Case closure approved",
            )

        case.status = "in_progress"
        case.updated_at = now
        case.outcome_notes = payload.review_notes
        db.commit()
        return ReviewActionResponse(
            success=True,
            review_status="returned",
            updated_status=case.status,
            message="Case returned to analyst",
        )

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        if payload.decision == "approve":
            decision.status = "approved"
            decision.approver_id = current_user.user_id
            decision.approved_at = now
            db.commit()
            return ReviewActionResponse(
                success=True,
                review_status="approved",
                updated_status=decision.status,
                message="Decision approved",
            )

        decision.status = "rejected"
        decision.rejection_reason = payload.review_notes
        decision.approver_id = current_user.user_id
        decision.approved_at = now
        db.commit()
        return ReviewActionResponse(
            success=True,
            review_status="returned",
            updated_status=decision.status,
            message="Decision returned to submitter",
        )

    raise HTTPException(status_code=400, detail="Unsupported work item kind")

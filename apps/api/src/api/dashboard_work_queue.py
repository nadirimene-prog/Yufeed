"""AMLCO command center work-queue and work-item workflow APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload

from src.audit.models import EventRecord
from src.audit.recorders import record_event
from src.auth.dependencies import CurrentUser, require_any_role
from src.config import settings
from src.database import get_db
from src.models.case_decision import CaseDecision
from src.models.tenant_models import Tenant, TenantUser
from src.models.transaction_models import Alert, Case, Transaction
from src.schemas.dashboard_v3 import (
    ActionHistoryItem,
    AiRecommendation,
    DecisionTrace,
    DashboardWorkQueueItem,
    DashboardWorkQueueResponse,
    EvidenceChecklistItem,
    FreshnessMeta,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewProvenance,
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
EVENT_TYPE_LABELS: dict[str, str] = {
    "dashboard.alert.assigned": "Alert Assigned",
    "dashboard.alert.escalated": "Alert Escalated",
    "dashboard.alert.marked_in_progress": "Alert Marked In Progress",
    "dashboard.alert.case_created": "Case Created From Alert",
    "dashboard.alert.closed": "Alert Closed",
    "dashboard.alert.review.approved": "Alert Review Approved",
    "dashboard.alert.review.returned": "Alert Review Returned",
    "dashboard.case.assigned": "Case Assigned",
    "dashboard.case.escalated": "Case Escalated",
    "dashboard.case.marked_in_progress": "Case Marked In Progress",
    "dashboard.case.created_from_alert": "Case Created From Alert",
    "dashboard.case.closed": "Case Closed",
    "dashboard.case.review.approved": "Case Review Approved",
    "dashboard.case.review.returned": "Case Review Returned",
    "dashboard.approval.closed": "Approval Closed",
    "dashboard.approval.review.approved": "Approval Review Approved",
    "dashboard.approval.review.returned": "Approval Review Returned",
}


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


def _freshness_meta(
    *,
    generated_at: datetime,
    stale_after_seconds: int,
    source_watermark_at: datetime | None = None,
) -> FreshnessMeta:
    source_lag_seconds = (
        max(0, int((generated_at - source_watermark_at).total_seconds()))
        if source_watermark_at is not None
        else None
    )
    return FreshnessMeta(
        generated_at=generated_at,
        stale_after_seconds=stale_after_seconds,
        source_watermark_at=source_watermark_at,
        source_lag_seconds=source_lag_seconds,
    )


def _normalize_entity_type(value: str | None, fallback: str = "user") -> str:
    normalized = (value or fallback).strip().lower()
    if normalized in {"user", "business", "account", "transaction", "pattern"}:
        return normalized
    return fallback


def _event_payload_dict(event: EventRecord) -> dict:
    return event.payload if isinstance(event.payload, dict) else {}


def _event_label(event_type: str) -> str:
    if event_type in EVENT_TYPE_LABELS:
        return EVENT_TYPE_LABELS[event_type]
    if event_type.startswith("dashboard."):
        event_type = event_type.removeprefix("dashboard.")
    return event_type.replace(".", " ").replace("_", " ").strip().title() or "Event"


def _event_detail(event: EventRecord) -> str | None:
    payload = _event_payload_dict(event)
    parts: list[str] = []
    for key in ("action", "decision", "status"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    notes = payload.get("notes")
    if isinstance(notes, str) and notes.strip():
        parts.append(notes.strip())
    return " • ".join(parts) if parts else None


def _event_actor(event: EventRecord) -> str:
    payload = _event_payload_dict(event)
    for key in ("actor_id", "reviewer_id", "assignee"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    if isinstance(event.source, str) and event.source.strip():
        return event.source
    return "system"


def _work_item_event_records(
    *,
    db: Session,
    current_user: CurrentUser,
    entity_type: str,
    entity_id: str,
) -> list[EventRecord]:
    query = db.query(EventRecord).filter(
        EventRecord.entity_type == entity_type,
        EventRecord.entity_id == entity_id,
    )
    if current_user.tenant_id:
        query = query.filter(EventRecord.tenant_id == current_user.tenant_id)
    return query.order_by(EventRecord.created_at.asc()).all()


def _event_backed_history(
    events: list[EventRecord],
) -> tuple[list[WorkItemTimelineEvent], list[ActionHistoryItem]]:
    timeline: list[WorkItemTimelineEvent] = []
    actions: list[ActionHistoryItem] = []
    for event in events:
        at = _as_utc(event.created_at)
        if at is None:
            continue
        label = _event_label(event.event_type)
        detail = _event_detail(event)
        timeline.append(WorkItemTimelineEvent(at=at, label=label, detail=detail))
        actions.append(
            ActionHistoryItem(
                at=at,
                actor=_event_actor(event),
                action=event.event_type,
                notes=detail,
            )
        )
    return timeline, actions


def _decision_trace_payload(trace: DecisionTrace) -> dict:
    return {
        "facts_used": list(trace.facts_used),
        "policy_rules_triggered": list(trace.policy_rules_triggered),
        "ai_summary": trace.ai_summary,
        "ai_confidence": trace.ai_confidence,
        "human_decision": trace.human_decision,
        "override_reason": trace.override_reason,
    }


def _decision_trace_from_events(events: list[EventRecord]) -> DecisionTrace | None:
    for event in reversed(events):
        payload = _event_payload_dict(event)
        raw = payload.get("decision_trace")
        if not isinstance(raw, dict):
            continue
        facts_used = [value for value in (raw.get("facts_used") or []) if isinstance(value, str)]
        policy_rules_triggered = [
            value for value in (raw.get("policy_rules_triggered") or []) if isinstance(value, str)
        ]
        ai_summary = raw.get("ai_summary") if isinstance(raw.get("ai_summary"), str) else None
        ai_confidence_raw = raw.get("ai_confidence")
        ai_confidence = (
            float(ai_confidence_raw) if isinstance(ai_confidence_raw, (int, float)) else None
        )
        human_decision = (
            raw.get("human_decision") if isinstance(raw.get("human_decision"), str) else None
        )
        override_reason = (
            raw.get("override_reason") if isinstance(raw.get("override_reason"), str) else None
        )
        return DecisionTrace(
            facts_used=facts_used,
            policy_rules_triggered=policy_rules_triggered,
            ai_summary=ai_summary,
            ai_confidence=ai_confidence,
            human_decision=human_decision,
            override_reason=override_reason,
        )
    return None


def _has_initialized_sar_template(case: Case) -> bool:
    evidence = case.evidence if isinstance(case.evidence, dict) else {}
    sar_draft = evidence.get("sar_draft")
    sar_lifecycle = evidence.get("sar_lifecycle")
    sar_id = evidence.get("sar_id")
    return bool(sar_id or sar_draft or sar_lifecycle)


def _record_dashboard_work_item_event(
    *,
    db: Session,
    current_user: CurrentUser,
    entity_type: str,
    entity_id: str,
    event_type: str,
    payload: dict | None = None,
):
    record_event(
        db,
        event_type=event_type,
        tenant_id=current_user.tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        source="dashboard_work_queue",
        payload=payload or {},
    )


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


def _alert_breached_condition(now: datetime):
    return or_(
        and_(
            or_(Alert.priority == 1, Alert.severity == "critical"),
            Alert.created_at < now - timedelta(hours=2),
        ),
        and_(Alert.severity == "high", Alert.created_at < now - timedelta(hours=8)),
        and_(Alert.severity == "medium", Alert.created_at < now - timedelta(hours=24)),
        and_(Alert.severity == "low", Alert.created_at < now - timedelta(hours=48)),
    )


def _alert_warning_condition(now: datetime):
    return or_(
        and_(
            or_(Alert.priority == 1, Alert.severity == "critical"),
            Alert.created_at >= now - timedelta(hours=2),
        ),
        and_(
            Alert.severity == "high",
            Alert.created_at <= now - timedelta(hours=4),
            Alert.created_at > now - timedelta(hours=8),
        ),
        and_(
            Alert.severity == "medium",
            Alert.created_at <= now - timedelta(hours=20),
            Alert.created_at > now - timedelta(hours=24),
        ),
        and_(
            Alert.severity == "low",
            Alert.created_at <= now - timedelta(hours=44),
            Alert.created_at > now - timedelta(hours=48),
        ),
    )


def _alert_sla_query_filter(value: str, now: datetime):
    normalized = value.lower()
    if normalized == "breached":
        return _alert_breached_condition(now)
    if normalized == "warning":
        return _alert_warning_condition(now)
    if normalized == "ok":
        return or_(
            and_(Alert.severity == "high", Alert.created_at > now - timedelta(hours=4)),
            and_(Alert.severity == "medium", Alert.created_at > now - timedelta(hours=20)),
            and_(Alert.severity == "low", Alert.created_at > now - timedelta(hours=44)),
        )
    if normalized == "none":
        return Alert.id == -1
    return None


def _case_priority_values_for_severity(value: str) -> list[str]:
    normalized = value.lower()
    if normalized == "critical":
        return ["critical", "urgent", "p1"]
    if normalized == "high":
        return ["high", "p2"]
    if normalized == "medium":
        return ["medium"]
    if normalized == "low":
        return ["low"]
    return []


def _case_breached_condition(now: datetime):
    return or_(
        and_(
            Case.priority.in_(["critical", "urgent", "p1"]),
            Case.opened_at < now - timedelta(hours=2),
        ),
        and_(Case.priority.in_(["high", "p2"]), Case.opened_at < now - timedelta(hours=8)),
        and_(Case.priority == "medium", Case.opened_at < now - timedelta(hours=24)),
        and_(Case.priority == "low", Case.opened_at < now - timedelta(hours=48)),
    )


def _case_warning_condition(now: datetime):
    return or_(
        and_(
            Case.priority.in_(["critical", "urgent", "p1"]),
            Case.opened_at >= now - timedelta(hours=2),
        ),
        and_(
            Case.priority.in_(["high", "p2"]),
            Case.opened_at <= now - timedelta(hours=4),
            Case.opened_at > now - timedelta(hours=8),
        ),
        and_(
            Case.priority == "medium",
            Case.opened_at <= now - timedelta(hours=20),
            Case.opened_at > now - timedelta(hours=24),
        ),
        and_(
            Case.priority == "low",
            Case.opened_at <= now - timedelta(hours=44),
            Case.opened_at > now - timedelta(hours=48),
        ),
    )


def _case_sla_query_filter(value: str, now: datetime):
    normalized = value.lower()
    if normalized == "breached":
        return _case_breached_condition(now)
    if normalized == "warning":
        return _case_warning_condition(now)
    if normalized == "ok":
        return or_(
            and_(Case.priority.in_(["high", "p2"]), Case.opened_at > now - timedelta(hours=4)),
            and_(Case.priority == "medium", Case.opened_at > now - timedelta(hours=20)),
            and_(Case.priority == "low", Case.opened_at > now - timedelta(hours=44)),
        )
    if normalized == "none":
        return Case.opened_at.is_(None)
    return None


def _priority_breached_condition(
    priority_column,
    timestamp_column,
    now: datetime,
):
    return or_(
        and_(
            priority_column.in_(["critical", "urgent", "p1"]),
            timestamp_column < now - timedelta(hours=2),
        ),
        and_(
            priority_column.in_(["high", "p2"]),
            timestamp_column < now - timedelta(hours=8),
        ),
        and_(priority_column == "medium", timestamp_column < now - timedelta(hours=24)),
        and_(priority_column == "low", timestamp_column < now - timedelta(hours=48)),
    )


def _priority_warning_condition(
    priority_column,
    timestamp_column,
    now: datetime,
):
    return or_(
        and_(
            priority_column.in_(["critical", "urgent", "p1"]),
            timestamp_column >= now - timedelta(hours=2),
        ),
        and_(
            priority_column.in_(["high", "p2"]),
            timestamp_column <= now - timedelta(hours=4),
            timestamp_column > now - timedelta(hours=8),
        ),
        and_(
            priority_column == "medium",
            timestamp_column <= now - timedelta(hours=20),
            timestamp_column > now - timedelta(hours=24),
        ),
        and_(
            priority_column == "low",
            timestamp_column <= now - timedelta(hours=44),
            timestamp_column > now - timedelta(hours=48),
        ),
    )


def _priority_sla_query_filter(
    value: str,
    priority_column,
    timestamp_column,
    now: datetime,
):
    normalized = value.lower()
    if normalized == "breached":
        return _priority_breached_condition(priority_column, timestamp_column, now)
    if normalized == "warning":
        return _priority_warning_condition(priority_column, timestamp_column, now)
    if normalized == "ok":
        return or_(
            and_(
                priority_column.in_(["high", "p2"]),
                timestamp_column > now - timedelta(hours=4),
            ),
            and_(priority_column == "medium", timestamp_column > now - timedelta(hours=20)),
            and_(priority_column == "low", timestamp_column > now - timedelta(hours=44)),
        )
    if normalized == "none":
        return timestamp_column.is_(None)
    return None


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
        entity_type="user",
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
        entity_type=_normalize_entity_type(case.subject_type, "user"),
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
        entity_type=_normalize_entity_type(
            parent_case.subject_type if parent_case else None, "user"
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
        entity_type=_normalize_entity_type(case.subject_type, "user"),
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


def _next_recommended_item_id(
    *,
    kind: WorkItemKind,
    item_id: str,
    db: Session,
    current_user: CurrentUser,
    now: datetime,
) -> str | None:
    def _as_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    current_numeric_id = _as_int(item_id)
    try:
        if kind == "alert":
            severity_rank = sa.case(
                (Alert.severity == "critical", 4),
                (Alert.severity == "high", 3),
                (Alert.severity == "medium", 2),
                else_=1,
            )
            query = (
                db.query(Alert)
                .options(joinedload(Alert.transaction))
                .filter(Alert.status.in_(["pending", "in_review"]))
            )
            query = _tenant_filter(query, Alert, current_user)
            if current_numeric_id is not None:
                query = query.filter(Alert.id != current_numeric_id)
            candidate = query.order_by(
                sa.case((_alert_breached_condition(now), 1), else_=0).desc(),
                severity_rank.desc(),
                sa.func.coalesce(Alert.risk_score, 0).desc(),
                Alert.created_at.asc(),
            ).first()
            return f"alert:{candidate.id}" if candidate else None
        elif kind in {"case", "reg_task"}:
            priority_rank = sa.case(
                (Case.priority.in_(["critical", "urgent", "p1"]), 4),
                (Case.priority.in_(["high", "p2"]), 3),
                (Case.priority == "medium", 2),
                else_=1,
            )
            query = db.query(Case).filter(Case.status.in_(["open", "in_progress"]))
            query = _tenant_filter(query, Case, current_user)
            if kind == "reg_task":
                query = query.filter(Case.outcome == "sar_required")
            if current_numeric_id is not None:
                query = query.filter(Case.id != current_numeric_id)
            candidate = query.order_by(
                sa.case((_case_breached_condition(now), 1), else_=0).desc(),
                priority_rank.desc(),
                Case.opened_at.asc(),
                Case.updated_at.asc(),
            ).first()
            if not candidate:
                return None
            prefix = "reg_task" if kind == "reg_task" else "case"
            return f"{prefix}:{candidate.id}"
        elif kind == "approval":
            decision_query = db.query(CaseDecision).filter(CaseDecision.status == "submitted")
            decision_query = _tenant_filter(decision_query, CaseDecision, current_user)
            if current_numeric_id is not None:
                decision_query = decision_query.filter(CaseDecision.id != current_numeric_id)
            candidate = decision_query.order_by(
                CaseDecision.updated_at.desc(),
                CaseDecision.created_at.desc(),
            ).first()
            return f"approval:{candidate.id}" if candidate else None
        else:
            return None
    except Exception:
        # Non-blocking hint only.
        return None


def _build_review_provenance_from_decision(
    decision: CaseDecision | None,
) -> ReviewProvenance | None:
    if not decision:
        return None
    status = (decision.status or "").lower()
    if status == "approved":
        outcome = "approved"
    elif status == "rejected":
        outcome = "returned"
    else:
        outcome = None
    return ReviewProvenance(
        submitted_by=decision.created_by,
        submitted_at=_as_utc(decision.submitted_at),
        reviewed_by=decision.approver_id,
        reviewed_at=_as_utc(decision.approved_at),
        review_outcome=outcome,
        return_reason=decision.rejection_reason,
    )


def _build_decision_trace(
    *,
    queue_item: DashboardWorkQueueItem,
    ai_recommendation: AiRecommendation,
    human_decision: str | None = None,
    override_reason: str | None = None,
) -> DecisionTrace:
    return DecisionTrace(
        facts_used=[
            f"severity={queue_item.severity}",
            f"sla_status={queue_item.sla_status}",
            f"risk_score={queue_item.risk_score:.0f}",
            f"jurisdiction={queue_item.jurisdiction}",
        ],
        policy_rules_triggered=list(queue_item.review_requirement.reasons),
        ai_summary=ai_recommendation.summary,
        ai_confidence=ai_recommendation.confidence,
        human_decision=human_decision,
        override_reason=override_reason,
    )


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


def _build_ai_recommendation(
    item: DashboardWorkQueueItem,
    alert: Alert | None = None,
) -> AiRecommendation:
    fallback_confidence = 0.92 if item.severity in {"high", "critical"} else 0.74
    fallback_summary = (
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

    if alert is not None:
        prediction = (alert.ml_prediction or "").strip().lower()
        confidence_raw = _to_float(alert.ml_confidence) if alert.ml_confidence is not None else None
        confidence = (
            max(0.0, min(1.0, confidence_raw))
            if confidence_raw is not None
            else fallback_confidence
        )
        if prediction == "true_positive":
            summary = "Model indicates elevated true-positive risk. Escalate and preserve evidence."
        elif prediction == "false_positive":
            summary = "Model indicates likely false positive. Validate context before closure."
        elif prediction == "uncertain":
            summary = "Model confidence is uncertain. Continue analyst triage with corroborating evidence."
        else:
            summary = fallback_summary

        if prediction:
            rationale.append(f"ml_prediction={prediction}")
        if confidence_raw is not None:
            rationale.append(f"ml_confidence={confidence:.2f}")
        if alert.ml_model_version:
            rationale.append(f"ml_model_version={alert.ml_model_version}")

        return AiRecommendation(summary=summary, confidence=confidence, rationale=rationale)

    return AiRecommendation(
        summary=fallback_summary,
        confidence=fallback_confidence,
        rationale=rationale,
    )


def _alert_severity_rank_expression():
    return sa.case(
        (Alert.severity == "critical", 4),
        (Alert.severity == "high", 3),
        (Alert.severity == "medium", 2),
        else_=1,
    )


def _case_priority_rank_expression():
    return sa.case(
        (Case.priority.in_(["critical", "urgent", "p1"]), 4),
        (Case.priority.in_(["high", "p2"]), 3),
        (Case.priority == "medium", 2),
        else_=1,
    )


def _build_dashboard_queue_stage2(
    *,
    page: int,
    page_size: int,
    queue: str,
    severity: str | None,
    jurisdiction: str | None,
    sla: str | None,
    search: str | None,
    saved_view: str | None,
    db: Session,
    current_user: CurrentUser,
) -> DashboardWorkQueueResponse:
    now = utc_now()

    queue_value = (queue or "all").lower()
    if queue_value not in {"all", "alerts", "cases", "approvals", "reg_tasks"}:
        queue_value = "all"
    normalized_saved_view = (saved_view or "").strip().lower()
    normalized_severity = (severity or "").strip().lower()
    normalized_sla = (sla or "").strip().lower()
    normalized_jurisdiction = (jurisdiction or "").strip().upper()
    normalized_search = (search or "").strip()

    include_alerts = queue_value in {"all", "alerts"}
    include_cases = queue_value in {"all", "cases"}
    include_approvals = queue_value in {"all", "approvals"}
    include_reg_tasks = queue_value in {"all", "reg_tasks"}

    candidate_selects: list[sa.sql.Select] = []

    if include_alerts:
        alert_started_at = sa.func.coalesce(Alert.created_at, Alert.updated_at)
        alert_source_watermark = sa.func.coalesce(Alert.updated_at, Alert.created_at)
        alert_query = db.query(
            sa.literal("alert").label("kind"),
            Alert.id.label("record_id"),
            sa.case((_alert_breached_condition(now), 1), else_=0).label("sla_breached_rank"),
            _alert_severity_rank_expression().label("severity_rank"),
            sa.cast(sa.func.coalesce(Alert.risk_score, 0), sa.Float).label("risk_score"),
            alert_started_at.label("started_at"),
            alert_source_watermark.label("source_watermark"),
        ).filter(Alert.status.in_(["pending", "in_review"]))
        alert_query = _tenant_filter(alert_query, Alert, current_user)

        if normalized_saved_view == "my_queue":
            alert_query = alert_query.filter(Alert.assigned_to == current_user.user_id)

        if normalized_severity and normalized_severity != "all":
            alert_query = alert_query.filter(Alert.severity == normalized_severity)

        if normalized_sla and normalized_sla != "all":
            alert_sla_filter = _alert_sla_query_filter(normalized_sla, now)
            if alert_sla_filter is not None:
                alert_query = alert_query.filter(alert_sla_filter)

        needs_alert_txn_join = bool(normalized_jurisdiction and normalized_jurisdiction != "ALL")
        needs_alert_txn_join = needs_alert_txn_join or bool(normalized_search)
        if needs_alert_txn_join:
            alert_query = alert_query.outerjoin(Alert.transaction)
            if normalized_jurisdiction and normalized_jurisdiction != "ALL":
                alert_query = alert_query.filter(
                    Transaction.country_code == normalized_jurisdiction
                )
            if normalized_search:
                pattern = f"%{normalized_search.lower()}%"
                alert_query = alert_query.filter(
                    or_(
                        Alert.user_id.ilike(pattern),
                        Alert.alert_id.ilike(pattern),
                        Alert.alert_type.ilike(pattern),
                        Transaction.country_code.ilike(pattern),
                    )
                )

        candidate_selects.append(alert_query.statement)

    if include_cases:
        case_started_at = sa.func.coalesce(Case.opened_at, Case.updated_at, Case.created_at)
        case_source_watermark = sa.func.coalesce(Case.updated_at, Case.opened_at, Case.created_at)
        case_query = db.query(
            sa.literal("case").label("kind"),
            Case.id.label("record_id"),
            sa.case((_case_breached_condition(now), 1), else_=0).label("sla_breached_rank"),
            _case_priority_rank_expression().label("severity_rank"),
            sa.cast(sa.literal(0.0), sa.Float).label("risk_score"),
            case_started_at.label("started_at"),
            case_source_watermark.label("source_watermark"),
        ).filter(Case.status.in_(["open", "in_progress"]))
        case_query = _tenant_filter(case_query, Case, current_user)

        if normalized_saved_view == "my_queue":
            case_query = case_query.filter(Case.assigned_to == current_user.user_id)

        if normalized_severity and normalized_severity != "all":
            priority_values = _case_priority_values_for_severity(normalized_severity)
            if priority_values:
                case_query = case_query.filter(Case.priority.in_(priority_values))
            else:
                case_query = case_query.filter(Case.id == -1)

        if normalized_sla and normalized_sla != "all":
            case_sla_filter = _case_sla_query_filter(normalized_sla, now)
            if case_sla_filter is not None:
                case_query = case_query.filter(case_sla_filter)

        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            case_query = case_query.filter(
                or_(
                    Case.subject_id.ilike(pattern),
                    Case.case_id.ilike(pattern),
                    Case.case_type.ilike(pattern),
                )
            )

        candidate_selects.append(case_query.statement)

    if include_reg_tasks:
        reg_started_at = sa.func.coalesce(Case.opened_at, Case.updated_at, Case.created_at)
        reg_source_watermark = sa.func.coalesce(Case.updated_at, Case.opened_at, Case.created_at)
        reg_task_query = db.query(
            sa.literal("reg_task").label("kind"),
            Case.id.label("record_id"),
            sa.case((Case.opened_at < now - timedelta(hours=8), 1), else_=0).label(
                "sla_breached_rank"
            ),
            sa.literal(3).label("severity_rank"),
            sa.cast(sa.literal(0.0), sa.Float).label("risk_score"),
            reg_started_at.label("started_at"),
            reg_source_watermark.label("source_watermark"),
        ).filter(
            Case.status.in_(["open", "in_progress"]),
            Case.outcome == "sar_required",
        )
        reg_task_query = _tenant_filter(reg_task_query, Case, current_user)

        if normalized_saved_view == "my_queue":
            reg_task_query = reg_task_query.filter(Case.assigned_to == current_user.user_id)

        if normalized_severity and normalized_severity not in {"", "all", "high"}:
            reg_task_query = reg_task_query.filter(Case.id == -1)

        if normalized_sla and normalized_sla != "all":
            if normalized_sla == "none":
                reg_task_query = reg_task_query.filter(Case.id == -1)
            elif normalized_sla == "breached":
                reg_task_query = reg_task_query.filter(Case.opened_at < now - timedelta(hours=8))
            elif normalized_sla == "warning":
                reg_task_query = reg_task_query.filter(
                    and_(
                        Case.opened_at <= now - timedelta(hours=4),
                        Case.opened_at > now - timedelta(hours=8),
                    )
                )
            elif normalized_sla == "ok":
                reg_task_query = reg_task_query.filter(Case.opened_at > now - timedelta(hours=4))

        if normalized_search and "sar_deadline" not in normalized_search.lower():
            pattern = f"%{normalized_search.lower()}%"
            reg_task_query = reg_task_query.filter(
                or_(
                    Case.subject_id.ilike(pattern),
                    Case.case_id.ilike(pattern),
                    Case.case_type.ilike(pattern),
                )
            )

        candidate_selects.append(reg_task_query.statement)

    if include_approvals:
        approval_started_at = sa.func.coalesce(CaseDecision.submitted_at, CaseDecision.created_at)
        approval_source_watermark = sa.func.coalesce(
            CaseDecision.updated_at, CaseDecision.created_at
        )
        approval_query = (
            db.query(
                sa.literal("approval").label("kind"),
                CaseDecision.id.label("record_id"),
                sa.case(
                    (
                        _priority_breached_condition(Case.priority, approval_started_at, now),
                        1,
                    ),
                    else_=0,
                ).label("sla_breached_rank"),
                _case_priority_rank_expression().label("severity_rank"),
                sa.cast(sa.literal(0.0), sa.Float).label("risk_score"),
                approval_started_at.label("started_at"),
                approval_source_watermark.label("source_watermark"),
            )
            .join(Case, Case.id == CaseDecision.case_id)
            .filter(CaseDecision.status == "submitted")
        )
        approval_query = _tenant_filter(approval_query, CaseDecision, current_user)
        approval_query = _tenant_filter(approval_query, Case, current_user)

        if normalized_saved_view == "my_queue":
            approval_query = approval_query.filter(CaseDecision.approver_id == current_user.user_id)

        if normalized_severity and normalized_severity != "all":
            priority_values = _case_priority_values_for_severity(normalized_severity)
            if priority_values:
                approval_query = approval_query.filter(Case.priority.in_(priority_values))
            else:
                approval_query = approval_query.filter(Case.id == -1)

        if normalized_sla and normalized_sla != "all":
            approval_sla_filter = _priority_sla_query_filter(
                normalized_sla,
                Case.priority,
                approval_started_at,
                now,
            )
            if approval_sla_filter is not None:
                approval_query = approval_query.filter(approval_sla_filter)

        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            approval_query = approval_query.filter(
                or_(
                    Case.subject_id.ilike(pattern),
                    Case.case_id.ilike(pattern),
                    Case.case_type.ilike(pattern),
                    sa.cast(CaseDecision.id, sa.String).ilike(pattern),
                )
            )

        candidate_selects.append(approval_query.statement)

    if not candidate_selects:
        return DashboardWorkQueueResponse(
            page=page,
            page_size=page_size,
            total=0,
            items=[],
            freshness=_freshness_meta(
                generated_at=now,
                stale_after_seconds=60,
                source_watermark_at=None,
            ),
        )

    union_subquery = sa.union_all(*candidate_selects).subquery("work_queue_candidates")
    filtered_stmt = sa.select(
        union_subquery.c.kind,
        union_subquery.c.record_id,
        union_subquery.c.sla_breached_rank,
        union_subquery.c.severity_rank,
        union_subquery.c.risk_score,
        union_subquery.c.started_at,
        union_subquery.c.source_watermark,
    )

    if normalized_saved_view == "escalations":
        filtered_stmt = filtered_stmt.where(
            or_(
                union_subquery.c.sla_breached_rank == 1,
                union_subquery.c.severity_rank >= 3,
            )
        )

    filtered_subquery = filtered_stmt.subquery("work_queue_filtered")
    total = int(db.execute(sa.select(sa.func.count()).select_from(filtered_subquery)).scalar_one())
    latest_source = db.execute(
        sa.select(sa.func.max(filtered_subquery.c.source_watermark))
    ).scalar_one()

    page_rows = db.execute(
        sa.select(
            filtered_subquery.c.kind,
            filtered_subquery.c.record_id,
        )
        .order_by(
            filtered_subquery.c.sla_breached_rank.desc(),
            filtered_subquery.c.severity_rank.desc(),
            filtered_subquery.c.risk_score.desc(),
            filtered_subquery.c.started_at.asc(),
            filtered_subquery.c.kind.asc(),
            filtered_subquery.c.record_id.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    alert_ids = [int(row.record_id) for row in page_rows if row.kind == "alert"]
    case_ids = [int(row.record_id) for row in page_rows if row.kind == "case"]
    reg_task_ids = [int(row.record_id) for row in page_rows if row.kind == "reg_task"]
    approval_ids = [int(row.record_id) for row in page_rows if row.kind == "approval"]

    alerts_by_id: dict[int, Alert] = {}
    if alert_ids:
        alert_query = (
            db.query(Alert).options(joinedload(Alert.transaction)).filter(Alert.id.in_(alert_ids))
        )
        alert_query = _tenant_filter(alert_query, Alert, current_user)
        alerts_by_id = {row.id: row for row in alert_query.all()}

    decisions_by_id: dict[int, CaseDecision] = {}
    if approval_ids:
        decision_query = db.query(CaseDecision).filter(CaseDecision.id.in_(approval_ids))
        decision_query = _tenant_filter(decision_query, CaseDecision, current_user)
        decisions_by_id = {row.id: row for row in decision_query.all()}

    all_case_ids: set[int] = set(case_ids)
    all_case_ids.update(reg_task_ids)
    all_case_ids.update(
        decision.case_id
        for decision in decisions_by_id.values()
        if isinstance(decision.case_id, int)
    )
    cases_by_id: dict[int, Case] = {}
    if all_case_ids:
        case_query = db.query(Case).filter(Case.id.in_(all_case_ids))
        case_query = _tenant_filter(case_query, Case, current_user)
        cases_by_id = {row.id: row for row in case_query.all()}

    transaction_ids: set[int] = set()
    for case_id in {*case_ids, *reg_task_ids}:
        case = cases_by_id.get(case_id)
        if not case:
            continue
        for txn_id in case.related_transaction_ids or []:
            if isinstance(txn_id, int):
                transaction_ids.add(txn_id)

    transaction_lookup: dict[int, Transaction] = {}
    if transaction_ids:
        txn_query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
        txn_query = _tenant_filter(txn_query, Transaction, current_user)
        transaction_lookup = {row.id: row for row in txn_query.all()}

    items: list[DashboardWorkQueueItem] = []
    for row in page_rows:
        record_id = int(row.record_id)
        if row.kind == "alert":
            alert = alerts_by_id.get(record_id)
            if alert:
                items.append(_alert_queue_item(alert, now))
        elif row.kind == "case":
            case = cases_by_id.get(record_id)
            if case:
                items.append(_case_queue_item(case, now, transaction_lookup))
        elif row.kind == "reg_task":
            case = cases_by_id.get(record_id)
            if case and (case.outcome or "").lower() == "sar_required":
                items.append(_reg_task_queue_item(case, now))
        elif row.kind == "approval":
            decision = decisions_by_id.get(record_id)
            if not decision:
                continue
            parent_case = cases_by_id.get(decision.case_id)
            if parent_case:
                items.append(_approval_queue_item(decision, {parent_case.id: parent_case}, now))

    return DashboardWorkQueueResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=items,
        freshness=_freshness_meta(
            generated_at=now,
            stale_after_seconds=60,
            source_watermark_at=_as_utc(latest_source),
        ),
    )


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

    queue_value = (queue or "all").lower()
    if queue_value not in {"all", "alerts", "cases", "approvals", "reg_tasks"}:
        queue_value = "all"
    normalized_jurisdiction = (jurisdiction or "").strip().upper()
    queue_includes_non_alert = queue_value in {"all", "cases", "approvals", "reg_tasks"}

    # Jurisdiction for case/approval/reg_task is derived from related transactions in Python.
    # Keep Stage 1 behavior for that compatibility path.
    if normalized_jurisdiction and normalized_jurisdiction != "ALL" and queue_includes_non_alert:
        return _get_dashboard_work_queue_stage1(
            page=page,
            page_size=page_size,
            queue=queue,
            severity=severity,
            jurisdiction=jurisdiction,
            sla=sla,
            search=search,
            saved_view=saved_view,
            db=db,
            current_user=current_user,
        )

    return _build_dashboard_queue_stage2(
        page=page,
        page_size=page_size,
        queue=queue,
        severity=severity,
        jurisdiction=jurisdiction,
        sla=sla,
        search=search,
        saved_view=saved_view,
        db=db,
        current_user=current_user,
    )


def _get_dashboard_work_queue_stage1(
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

    queue_value = (queue or "all").lower()
    if queue_value not in {"all", "alerts", "cases", "approvals", "reg_tasks"}:
        queue_value = "all"
    normalized_saved_view = (saved_view or "").strip().lower()
    normalized_severity = (severity or "").strip().lower()
    normalized_sla = (sla or "").strip().lower()
    normalized_jurisdiction = (jurisdiction or "").strip().upper()
    normalized_search = (search or "").strip()

    include_alerts = queue_value in {"all", "alerts"}
    include_cases = queue_value in {"all", "cases"}
    include_approvals = queue_value in {"all", "approvals"}
    include_reg_tasks = queue_value in {"all", "reg_tasks"}

    alerts: list[Alert] = []
    if include_alerts:
        alert_query = (
            db.query(Alert)
            .options(joinedload(Alert.transaction))
            .filter(Alert.status.in_(["pending", "in_review"]))
        )
        alert_query = _tenant_filter(alert_query, Alert, current_user)

        if normalized_saved_view == "my_queue":
            alert_query = alert_query.filter(Alert.assigned_to == current_user.user_id)
        elif normalized_saved_view == "escalations":
            alert_query = alert_query.filter(
                or_(_alert_breached_condition(now), Alert.severity.in_(["high", "critical"]))
            )

        if normalized_severity and normalized_severity != "all":
            alert_query = alert_query.filter(Alert.severity == normalized_severity)

        if normalized_sla and normalized_sla != "all":
            alert_sla_filter = _alert_sla_query_filter(normalized_sla, now)
            if alert_sla_filter is not None:
                alert_query = alert_query.filter(alert_sla_filter)

        needs_alert_txn_join = bool(normalized_jurisdiction and normalized_jurisdiction != "ALL")
        needs_alert_txn_join = needs_alert_txn_join or bool(normalized_search)
        if needs_alert_txn_join:
            alert_query = alert_query.outerjoin(Alert.transaction)
            if normalized_jurisdiction and normalized_jurisdiction != "ALL":
                alert_query = alert_query.filter(
                    Transaction.country_code == normalized_jurisdiction
                )
            if normalized_search:
                pattern = f"%{normalized_search.lower()}%"
                alert_query = alert_query.filter(
                    or_(
                        Alert.user_id.ilike(pattern),
                        Alert.alert_id.ilike(pattern),
                        Alert.alert_type.ilike(pattern),
                        Transaction.country_code.ilike(pattern),
                    )
                )
        alerts = alert_query.all()

    case_items_cases: list[Case] = []
    if include_cases:
        case_query = db.query(Case).filter(Case.status.in_(["open", "in_progress"]))
        case_query = _tenant_filter(case_query, Case, current_user)

        if normalized_saved_view == "my_queue":
            case_query = case_query.filter(Case.assigned_to == current_user.user_id)
        elif normalized_saved_view == "escalations":
            case_query = case_query.filter(
                or_(
                    _case_breached_condition(now),
                    Case.priority.in_(["high", "critical", "urgent", "p1", "p2"]),
                )
            )

        if normalized_severity and normalized_severity != "all":
            priority_values = _case_priority_values_for_severity(normalized_severity)
            if priority_values:
                case_query = case_query.filter(Case.priority.in_(priority_values))
            else:
                case_query = case_query.filter(Case.id == -1)

        if normalized_sla and normalized_sla != "all":
            case_sla_filter = _case_sla_query_filter(normalized_sla, now)
            if case_sla_filter is not None:
                case_query = case_query.filter(case_sla_filter)

        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            case_query = case_query.filter(
                or_(
                    Case.subject_id.ilike(pattern),
                    Case.case_id.ilike(pattern),
                    Case.case_type.ilike(pattern),
                )
            )

        case_items_cases = case_query.all()

    reg_task_cases: list[Case] = []
    if include_reg_tasks:
        reg_task_query = (
            db.query(Case)
            .filter(Case.status.in_(["open", "in_progress"]))
            .filter(Case.outcome == "sar_required")
        )
        reg_task_query = _tenant_filter(reg_task_query, Case, current_user)

        if normalized_saved_view == "my_queue":
            reg_task_query = reg_task_query.filter(Case.assigned_to == current_user.user_id)
        elif normalized_saved_view == "escalations":
            # Reg tasks always render as high severity in the queue item model, so this saved
            # view includes them all without an extra severity predicate.
            pass

        if normalized_severity and normalized_severity not in {"", "all", "high"}:
            reg_task_query = reg_task_query.filter(Case.id == -1)

        if normalized_sla and normalized_sla != "all":
            if normalized_sla == "none":
                reg_task_query = reg_task_query.filter(Case.id == -1)
            else:
                # Reg tasks use the case open timestamp but a fixed "high" severity deadline (8h).
                # Translate the filter into open_at windows independent of stored case priority.
                if normalized_sla == "breached":
                    reg_task_query = reg_task_query.filter(
                        Case.opened_at < now - timedelta(hours=8)
                    )
                elif normalized_sla == "warning":
                    reg_task_query = reg_task_query.filter(
                        and_(
                            Case.opened_at <= now - timedelta(hours=4),
                            Case.opened_at > now - timedelta(hours=8),
                        )
                    )
                elif normalized_sla == "ok":
                    reg_task_query = reg_task_query.filter(
                        Case.opened_at > now - timedelta(hours=4)
                    )

        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            if "sar_deadline" not in normalized_search.lower():
                reg_task_query = reg_task_query.filter(
                    or_(
                        Case.subject_id.ilike(pattern),
                        Case.case_id.ilike(pattern),
                        Case.case_type.ilike(pattern),
                    )
                )

        reg_task_cases = reg_task_query.all()

    decisions: list[CaseDecision] = []
    approval_case_lookup: dict[int, Case] = {}
    if include_approvals:
        decision_query = db.query(CaseDecision).filter(CaseDecision.status == "submitted")
        decision_query = _tenant_filter(decision_query, CaseDecision, current_user)

        if normalized_saved_view == "my_queue":
            decision_query = decision_query.filter(CaseDecision.approver_id == current_user.user_id)

        decisions = decision_query.all()

        if decisions:
            approval_case_ids = [
                decision.case_id for decision in decisions if decision.case_id is not None
            ]
            if approval_case_ids:
                approval_case_query = db.query(Case).filter(Case.id.in_(approval_case_ids))
                approval_case_query = _tenant_filter(approval_case_query, Case, current_user)

                if normalized_severity and normalized_severity != "all":
                    priority_values = _case_priority_values_for_severity(normalized_severity)
                    if priority_values:
                        approval_case_query = approval_case_query.filter(
                            Case.priority.in_(priority_values)
                        )
                    else:
                        approval_case_query = approval_case_query.filter(Case.id == -1)

                if normalized_search:
                    pattern = f"%{normalized_search.lower()}%"
                    approval_case_query = approval_case_query.filter(
                        or_(
                            Case.subject_id.ilike(pattern),
                            Case.case_id.ilike(pattern),
                            Case.case_type.ilike(pattern),
                        )
                    )

                approval_case_lookup = {case.id: case for case in approval_case_query.all()}
                decisions = [d for d in decisions if d.case_id in approval_case_lookup]
            else:
                decisions = []

    transaction_ids: set[int] = set()
    for case in case_items_cases:
        for txn_id in case.related_transaction_ids or []:
            if isinstance(txn_id, int):
                transaction_ids.add(txn_id)
    for case in reg_task_cases:
        for txn_id in case.related_transaction_ids or []:
            if isinstance(txn_id, int):
                transaction_ids.add(txn_id)
    for case in approval_case_lookup.values():
        for txn_id in case.related_transaction_ids or []:
            if isinstance(txn_id, int):
                transaction_ids.add(txn_id)

    transaction_lookup: dict[int, Transaction] = {}
    if transaction_ids:
        txn_query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
        txn_query = _tenant_filter(txn_query, Transaction, current_user)
        transaction_lookup = {row.id: row for row in txn_query.all()}

    merged_case_lookup: dict[int, Case] = {case.id: case for case in case_items_cases}
    merged_case_lookup.update(approval_case_lookup)

    items: list[DashboardWorkQueueItem] = []
    if include_alerts:
        items.extend(_alert_queue_item(alert, now) for alert in alerts)
    if include_cases:
        items.extend(_case_queue_item(case, now, transaction_lookup) for case in case_items_cases)
    if include_approvals:
        items.extend(
            _approval_queue_item(decision, merged_case_lookup, now) for decision in decisions
        )
    if include_reg_tasks:
        items.extend(
            _reg_task_queue_item(case, now)
            for case in reg_task_cases
            if (case.outcome or "").lower() == "sar_required"
        )

    # Compatibility pass for filters whose values are derived in Python (jurisdiction from related
    # transactions, approval SLA from parent-case severity, and exact search parity across item kinds).
    if normalized_saved_view == "my_queue":
        items = [item for item in items if item.owner == current_user.user_id]
    elif normalized_saved_view == "escalations":
        items = [
            item
            for item in items
            if item.sla_status == "breached" or item.severity in {"high", "critical"}
        ]

    if normalized_severity and normalized_severity not in {"", "all"}:
        items = [item for item in items if item.severity.lower() == normalized_severity]

    if normalized_jurisdiction and normalized_jurisdiction not in {"", "ALL"}:
        items = [item for item in items if item.jurisdiction.upper() == normalized_jurisdiction]

    if normalized_sla and normalized_sla not in {"", "all"}:
        items = [item for item in items if item.sla_status == normalized_sla]

    if normalized_search:
        needle = normalized_search.lower()
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

    source_watermarks: list[datetime] = []
    for alert in alerts:
        candidate = _as_utc(alert.updated_at) or _as_utc(alert.created_at)
        if candidate:
            source_watermarks.append(candidate)
    watermark_cases: dict[int, Case] = {case.id: case for case in case_items_cases}
    watermark_cases.update({case.id: case for case in reg_task_cases})
    watermark_cases.update(approval_case_lookup)
    for case in watermark_cases.values():
        candidate = _as_utc(case.updated_at) or _as_utc(case.opened_at)
        if candidate:
            source_watermarks.append(candidate)
    for decision in decisions:
        candidate = _as_utc(decision.updated_at) or _as_utc(decision.created_at)
        if candidate:
            source_watermarks.append(candidate)
    latest_source = max(source_watermarks) if source_watermarks else None

    return DashboardWorkQueueResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=page_items,
        freshness=_freshness_meta(
            generated_at=now,
            stale_after_seconds=60,
            source_watermark_at=latest_source,
        ),
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
        ai_recommendation = _build_ai_recommendation(queue_item, alert=alert)
        fallback_timeline = [
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
            fallback_timeline.append(
                WorkItemTimelineEvent(
                    at=_as_utc(alert.resolved_at) or now,
                    label="Resolved",
                    detail=alert.resolution_status or "resolved",
                )
            )
        alert_events = _work_item_event_records(
            db=db,
            current_user=current_user,
            entity_type="alert",
            entity_id=alert.alert_id,
        )
        event_timeline, event_actions = _event_backed_history(alert_events)
        timeline = (
            sorted(event_timeline, key=lambda item: item.at)
            if event_timeline
            else sorted(fallback_timeline, key=lambda item: item.at)
        )
        persisted_decision_trace = _decision_trace_from_events(alert_events)

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
        actions = event_actions or [
            ActionHistoryItem(
                at=_as_utc(alert.updated_at) or _as_utc(alert.created_at) or now,
                actor=alert.resolved_by or "system",
                action="alert_status_sync",
                notes=alert.status,
            )
        ]
        freshness = _freshness_meta(
            generated_at=now,
            stale_after_seconds=30,
            source_watermark_at=_as_utc(alert.updated_at) or _as_utc(alert.created_at),
        )

        return WorkItemDetailResponse(
            work_item=queue_item,
            context_timeline=timeline,
            linked_entities=linked_entities,
            linked_transactions=linked_transactions,
            ai_recommendation=ai_recommendation,
            narrative=alert.description or "",
            evidence_checklist=evidence,
            action_history=actions,
            review_requirement=queue_item.review_requirement,
            allowed_actions=["assign", "escalate", "mark_in_progress", "create_case", "close"],
            freshness=freshness,
            review_provenance=ReviewProvenance(
                submitted_by=alert.assigned_to,
                submitted_at=_as_utc(alert.updated_at),
                reviewed_by=alert.resolved_by,
                reviewed_at=_as_utc(alert.resolved_at),
                review_outcome=(
                    "approved"
                    if (alert.resolution_status or "").lower() == "review_approved"
                    else None
                ),
                return_reason=None,
            ),
            decision_trace=(
                persisted_decision_trace
                or _build_decision_trace(
                    queue_item=queue_item,
                    ai_recommendation=ai_recommendation,
                    human_decision=alert.resolution_status or alert.status,
                    override_reason=alert.resolution_notes,
                )
            ),
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
        ai_recommendation = _build_ai_recommendation(queue_item)
        latest_decision = (
            db.query(CaseDecision)
            .filter(CaseDecision.case_id == case.id)
            .order_by(CaseDecision.updated_at.desc(), CaseDecision.created_at.desc())
            .first()
        )

        fallback_timeline = [
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
            fallback_timeline.append(
                WorkItemTimelineEvent(
                    at=_as_utc(case.closed_at) or now,
                    label="Case closed",
                    detail=case.outcome,
                )
            )
        case_events = _work_item_event_records(
            db=db,
            current_user=current_user,
            entity_type="case",
            entity_id=case.case_id,
        )
        event_timeline, event_actions = _event_backed_history(case_events)
        timeline = (
            sorted(event_timeline, key=lambda item: item.at)
            if event_timeline
            else sorted(fallback_timeline, key=lambda item: item.at)
        )
        persisted_decision_trace = _decision_trace_from_events(case_events)

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
        actions = event_actions or [
            ActionHistoryItem(
                at=_as_utc(case.updated_at) or _as_utc(case.created_at) or now,
                actor=case.assigned_to or "system",
                action="case_status_sync",
                notes=case.status,
            )
        ]
        freshness = _freshness_meta(
            generated_at=now,
            stale_after_seconds=30,
            source_watermark_at=_as_utc(case.updated_at) or _as_utc(case.opened_at),
        )

        return WorkItemDetailResponse(
            work_item=queue_item,
            context_timeline=timeline,
            linked_entities=list(dict.fromkeys(linked_entities)),
            linked_transactions=linked_transactions,
            ai_recommendation=ai_recommendation,
            narrative=case.summary or case.description or "",
            evidence_checklist=evidence,
            action_history=actions,
            review_requirement=queue_item.review_requirement,
            allowed_actions=["assign", "escalate", "mark_in_progress", "close"],
            freshness=freshness,
            review_provenance=_build_review_provenance_from_decision(latest_decision),
            decision_trace=(
                persisted_decision_trace
                or _build_decision_trace(
                    queue_item=queue_item,
                    ai_recommendation=ai_recommendation,
                    human_decision=case.outcome or case.status,
                    override_reason=case.outcome_notes,
                )
            ),
        )

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        parent_case = _resolve_case(str(decision.case_id), db, current_user)
        queue_item = _approval_queue_item(decision, {parent_case.id: parent_case}, now)
        ai_recommendation = AiRecommendation(
            summary="Validate rationale and enforce 4-eyes policy before approval.",
            confidence=0.88,
            rationale=["approval_queue", "maker_checker_required"],
        )
        approval_events = _work_item_event_records(
            db=db,
            current_user=current_user,
            entity_type="case_decision",
            entity_id=str(decision.id),
        )
        approval_event_timeline, approval_event_actions = _event_backed_history(approval_events)
        approval_persisted_trace = _decision_trace_from_events(approval_events)
        fallback_approval_timeline = [
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
        ]
        approval_timeline = (
            sorted(approval_event_timeline, key=lambda item: item.at)
            if approval_event_timeline
            else sorted(fallback_approval_timeline, key=lambda item: item.at)
        )
        return WorkItemDetailResponse(
            work_item=queue_item,
            context_timeline=approval_timeline,
            linked_entities=[decision.created_by],
            linked_transactions=[],
            ai_recommendation=ai_recommendation,
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
            action_history=approval_event_actions,
            review_requirement=ReviewRequirement(required=True, reasons=["pending_approval"]),
            allowed_actions=["close"],
            freshness=_freshness_meta(
                generated_at=now,
                stale_after_seconds=30,
                source_watermark_at=_as_utc(decision.updated_at) or _as_utc(decision.created_at),
            ),
            review_provenance=_build_review_provenance_from_decision(decision),
            decision_trace=(
                approval_persisted_trace
                or DecisionTrace(
                    facts_used=["approval_queue", f"disposition={decision.disposition}"],
                    policy_rules_triggered=["maker_checker_required"],
                    ai_summary=ai_recommendation.summary,
                    ai_confidence=ai_recommendation.confidence,
                    human_decision=decision.status,
                    override_reason=decision.rejection_reason,
                )
            ),
        )

    case = _resolve_case(item_id, db, current_user)
    queue_item = _reg_task_queue_item(case, now)
    ai_recommendation = AiRecommendation(
        summary="Prepare SAR packet and route for compliance review.",
        confidence=0.84,
        rationale=["regulatory_deadline", "sar_required"],
    )
    latest_decision = (
        db.query(CaseDecision)
        .filter(CaseDecision.case_id == case.id)
        .order_by(CaseDecision.updated_at.desc(), CaseDecision.created_at.desc())
        .first()
    )
    reg_task_events = _work_item_event_records(
        db=db,
        current_user=current_user,
        entity_type="case",
        entity_id=case.case_id,
    )
    reg_timeline_events, reg_actions = _event_backed_history(reg_task_events)
    reg_persisted_trace = _decision_trace_from_events(reg_task_events)
    fallback_reg_timeline = [
        WorkItemTimelineEvent(
            at=_as_utc(case.opened_at) or now,
            label="Regulatory task created",
            detail="SAR filing window started",
        )
    ]
    reg_timeline = (
        sorted(reg_timeline_events, key=lambda item: item.at)
        if reg_timeline_events
        else sorted(fallback_reg_timeline, key=lambda item: item.at)
    )
    sar_template_initialized = _has_initialized_sar_template(case)

    return WorkItemDetailResponse(
        work_item=queue_item,
        context_timeline=reg_timeline,
        linked_entities=[case.subject_id] if case.subject_id else [],
        linked_transactions=[],
        ai_recommendation=ai_recommendation,
        narrative=case.summary or case.description or "",
        evidence_checklist=[
            EvidenceChecklistItem(
                id="sar-template",
                label="SAR template initialized",
                completed=sar_template_initialized,
            ),
            EvidenceChecklistItem(
                id="evidence-pack", label="Evidence pack attached", completed=bool(case.evidence)
            ),
        ],
        action_history=reg_actions
        or [
            ActionHistoryItem(
                at=_as_utc(case.updated_at) or _as_utc(case.created_at) or now,
                actor=case.assigned_to or "system",
                action="reg_task_status_sync",
                notes=case.status,
            )
        ],
        review_requirement=queue_item.review_requirement,
        allowed_actions=["mark_in_progress", "close"],
        freshness=_freshness_meta(
            generated_at=now,
            stale_after_seconds=30,
            source_watermark_at=_as_utc(case.updated_at) or _as_utc(case.opened_at),
        ),
        review_provenance=_build_review_provenance_from_decision(latest_decision),
        decision_trace=(
            reg_persisted_trace
            or _build_decision_trace(
                queue_item=queue_item,
                ai_recommendation=ai_recommendation,
                human_decision=case.outcome or case.status,
                override_reason=case.outcome_notes,
            )
        ),
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
        alert_queue_item = _alert_queue_item(alert, now)
        alert_ai_recommendation = _build_ai_recommendation(alert_queue_item, alert=alert)

        if payload.action == "assign":
            if not payload.assignee:
                raise HTTPException(
                    status_code=400, detail="assignee is required for assign action"
                )
            alert.assigned_to = payload.assignee
            alert.status = "in_review"
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="alert",
                entity_id=alert.alert_id,
                event_type="dashboard.alert.assigned",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "assignee": payload.assignee,
                    "status": alert.status,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=alert_queue_item,
                            ai_recommendation=alert_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Alert assigned",
                updated_status=alert.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        if payload.action == "escalate":
            alert.priority = 1
            alert.status = "in_review"
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="alert",
                entity_id=alert.alert_id,
                event_type="dashboard.alert.escalated",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": alert.status,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=alert_queue_item,
                            ai_recommendation=alert_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Alert escalated",
                updated_status=alert.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        if payload.action == "mark_in_progress":
            alert.status = "in_review"
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="alert",
                entity_id=alert.alert_id,
                event_type="dashboard.alert.marked_in_progress",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": alert.status,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=alert_queue_item,
                            ai_recommendation=alert_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Alert moved to in review",
                updated_status=alert.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
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
            case_transaction_lookup = (
                {alert.transaction_id: alert.transaction}
                if alert.transaction_id and alert.transaction is not None
                else {}
            )
            case_queue_item = _case_queue_item(case, now, case_transaction_lookup)
            case_ai_recommendation = _build_ai_recommendation(case_queue_item)
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="alert",
                entity_id=alert.alert_id,
                event_type="dashboard.alert.case_created",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": alert.status,
                    "created_case_id": case_id,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=alert_queue_item,
                            ai_recommendation=alert_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case",
                entity_id=case.case_id,
                event_type="dashboard.case.created_from_alert",
                payload={
                    "actor_id": current_user.user_id,
                    "source_alert_id": alert.alert_id,
                    "status": case.status,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=case_queue_item,
                            ai_recommendation=case_ai_recommendation,
                            human_decision="create_case",
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Case created from alert",
                updated_status=alert.status,
                created_case_id=case.case_id,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
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
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="alert",
                entity_id=alert.alert_id,
                event_type="dashboard.alert.closed",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": alert.status,
                    "notes": payload.notes,
                    "sar_required": bool(payload.sar_required),
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=queue_item,
                            ai_recommendation=alert_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Alert closed",
                updated_status=alert.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        raise HTTPException(status_code=400, detail="Unsupported action for alert")

    if kind in {"case", "reg_task"}:
        case = _resolve_case(item_id, db, current_user)
        transaction_lookup = {}
        transaction_ids = [
            txn_id for txn_id in case.related_transaction_ids or [] if isinstance(txn_id, int)
        ]
        if transaction_ids:
            query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
            query = _tenant_filter(query, Transaction, current_user)
            transaction_lookup = {row.id: row for row in query.all()}
        case_queue_item = _case_queue_item(case, now, transaction_lookup)
        case_ai_recommendation = _build_ai_recommendation(case_queue_item)

        if payload.action == "assign":
            if not payload.assignee:
                raise HTTPException(
                    status_code=400, detail="assignee is required for assign action"
                )
            case.assigned_to = payload.assignee
            case.status = "in_progress"
            case.updated_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case",
                entity_id=case.case_id,
                event_type="dashboard.case.assigned",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "assignee": payload.assignee,
                    "status": case.status,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=case_queue_item,
                            ai_recommendation=case_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Case assigned",
                updated_status=case.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        if payload.action == "escalate":
            case.priority = "high"
            case.status = "in_progress"
            case.updated_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case",
                entity_id=case.case_id,
                event_type="dashboard.case.escalated",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": case.status,
                    "priority": case.priority,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=case_queue_item,
                            ai_recommendation=case_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Case escalated",
                updated_status=case.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        if payload.action == "mark_in_progress":
            case.status = "in_progress"
            case.updated_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case",
                entity_id=case.case_id,
                event_type="dashboard.case.marked_in_progress",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": case.status,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=case_queue_item,
                            ai_recommendation=case_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Case in progress",
                updated_status=case.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        if payload.action == "close":
            if case_queue_item.review_requirement.required:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Close action requires reviewer approval",
                        "reasons": case_queue_item.review_requirement.reasons,
                    },
                )
            case.status = "closed"
            case.outcome = "sar_required" if payload.sar_required else "no_action"
            case.outcome_notes = payload.notes
            case.closed_at = now
            case.updated_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case",
                entity_id=case.case_id,
                event_type="dashboard.case.closed",
                payload={
                    "actor_id": current_user.user_id,
                    "action": payload.action,
                    "status": case.status,
                    "outcome": case.outcome,
                    "notes": payload.notes,
                    "sar_required": bool(payload.sar_required),
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=case_queue_item,
                            ai_recommendation=case_ai_recommendation,
                            human_decision=payload.action,
                            override_reason=payload.notes,
                        )
                    ),
                },
            )
            db.commit()
            return WorkItemActionResponse(
                success=True,
                message="Case closed",
                updated_status=case.status,
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        if payload.action == "create_case":
            raise HTTPException(
                status_code=400, detail="create_case is only available for alert items"
            )

        raise HTTPException(status_code=400, detail="Unsupported action for case")

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        parent_case = _resolve_case(str(decision.case_id), db, current_user)
        approval_queue_item = _approval_queue_item(decision, {parent_case.id: parent_case}, now)
        approval_ai_recommendation = AiRecommendation(
            summary="Validate rationale and enforce 4-eyes policy before approval.",
            confidence=0.88,
            rationale=["approval_queue", "maker_checker_required"],
        )
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
        _record_dashboard_work_item_event(
            db=db,
            current_user=current_user,
            entity_type="case_decision",
            entity_id=str(decision.id),
            event_type="dashboard.approval.closed",
            payload={
                "actor_id": current_user.user_id,
                "action": payload.action,
                "status": decision.status,
                "maker_user_id": decision.created_by,
                "decision_trace": _decision_trace_payload(
                    _build_decision_trace(
                        queue_item=approval_queue_item,
                        ai_recommendation=approval_ai_recommendation,
                        human_decision=payload.action,
                        override_reason=payload.notes,
                    )
                ),
            },
        )
        db.commit()
        return WorkItemActionResponse(
            success=True,
            message="Approval completed",
            updated_status=decision.status,
            next_recommended_item_id=_next_recommended_item_id(
                kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
            ),
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

    if kind == "alert":
        alert = _resolve_alert(item_id, db, current_user)
        alert_queue_item = _alert_queue_item(alert, now)
        alert_ai_recommendation = _build_ai_recommendation(alert_queue_item, alert=alert)
        if payload.decision == "approve":
            maker_user_id = (alert.assigned_to or "").strip()
            if not maker_user_id:
                raise HTTPException(
                    status_code=409,
                    detail="4-eyes violation: alert maker must be assigned before approval",
                )
            if maker_user_id == current_user.user_id:
                raise HTTPException(
                    status_code=409,
                    detail="4-eyes violation: approver cannot be the same as submitter",
                )
        if payload.decision == "approve":
            alert.status = "resolved"
            alert.resolution_status = "review_approved"
            alert.resolution_notes = payload.review_notes
            alert.resolved_by = current_user.user_id
            alert.resolved_at = now
            if payload.sar_required:
                alert.sar_filed = True
                alert.sar_filed_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="alert",
                entity_id=alert.alert_id,
                event_type="dashboard.alert.review.approved",
                payload={
                    "actor_id": current_user.user_id,
                    "decision": payload.decision,
                    "proposed_action": payload.proposed_action,
                    "status": alert.status,
                    "maker_user_id": alert.assigned_to,
                    "notes": payload.review_notes,
                    "sar_required": bool(payload.sar_required),
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=alert_queue_item,
                            ai_recommendation=alert_ai_recommendation,
                            human_decision=payload.decision,
                            override_reason=payload.review_notes,
                        )
                    ),
                },
            )
            db.commit()
            return ReviewActionResponse(
                success=True,
                review_status="approved",
                updated_status=alert.status,
                message="Alert closure approved",
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        alert.status = "in_review"
        alert.resolution_notes = payload.review_notes
        _record_dashboard_work_item_event(
            db=db,
            current_user=current_user,
            entity_type="alert",
            entity_id=alert.alert_id,
            event_type="dashboard.alert.review.returned",
            payload={
                "actor_id": current_user.user_id,
                "decision": payload.decision,
                "proposed_action": payload.proposed_action,
                "status": alert.status,
                "maker_user_id": alert.assigned_to,
                "notes": payload.review_notes,
                "decision_trace": _decision_trace_payload(
                    _build_decision_trace(
                        queue_item=alert_queue_item,
                        ai_recommendation=alert_ai_recommendation,
                        human_decision=payload.decision,
                        override_reason=payload.review_notes,
                    )
                ),
            },
        )
        db.commit()
        return ReviewActionResponse(
            success=True,
            review_status="returned",
            updated_status=alert.status,
            message="Alert returned for additional investigation",
            next_recommended_item_id=_next_recommended_item_id(
                kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
            ),
        )

    if kind in {"case", "reg_task"}:
        case = _resolve_case(item_id, db, current_user)
        transaction_lookup = {}
        transaction_ids = [
            txn_id for txn_id in case.related_transaction_ids or [] if isinstance(txn_id, int)
        ]
        if transaction_ids:
            query = db.query(Transaction).filter(Transaction.id.in_(transaction_ids))
            query = _tenant_filter(query, Transaction, current_user)
            transaction_lookup = {row.id: row for row in query.all()}
        case_queue_item = _case_queue_item(case, now, transaction_lookup)
        case_ai_recommendation = _build_ai_recommendation(case_queue_item)
        if payload.decision == "approve":
            maker_user_id = (case.assigned_to or "").strip()
            if not maker_user_id:
                raise HTTPException(
                    status_code=409,
                    detail="4-eyes violation: case maker must be assigned before approval",
                )
            if maker_user_id == current_user.user_id:
                raise HTTPException(
                    status_code=409,
                    detail="4-eyes violation: approver cannot be the same as submitter",
                )
        if payload.decision == "approve":
            case.status = "closed"
            case.closed_at = now
            case.outcome = "sar_required" if payload.sar_required else "no_action"
            case.outcome_notes = payload.review_notes
            case.updated_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case",
                entity_id=case.case_id,
                event_type="dashboard.case.review.approved",
                payload={
                    "actor_id": current_user.user_id,
                    "decision": payload.decision,
                    "proposed_action": payload.proposed_action,
                    "status": case.status,
                    "maker_user_id": case.assigned_to,
                    "notes": payload.review_notes,
                    "sar_required": bool(payload.sar_required),
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=case_queue_item,
                            ai_recommendation=case_ai_recommendation,
                            human_decision=payload.decision,
                            override_reason=payload.review_notes,
                        )
                    ),
                },
            )
            db.commit()
            return ReviewActionResponse(
                success=True,
                review_status="approved",
                updated_status=case.status,
                message="Case closure approved",
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        case.status = "in_progress"
        case.updated_at = now
        case.outcome_notes = payload.review_notes
        _record_dashboard_work_item_event(
            db=db,
            current_user=current_user,
            entity_type="case",
            entity_id=case.case_id,
            event_type="dashboard.case.review.returned",
            payload={
                "actor_id": current_user.user_id,
                "decision": payload.decision,
                "proposed_action": payload.proposed_action,
                "status": case.status,
                "maker_user_id": case.assigned_to,
                "notes": payload.review_notes,
                "decision_trace": _decision_trace_payload(
                    _build_decision_trace(
                        queue_item=case_queue_item,
                        ai_recommendation=case_ai_recommendation,
                        human_decision=payload.decision,
                        override_reason=payload.review_notes,
                    )
                ),
            },
        )
        db.commit()
        return ReviewActionResponse(
            success=True,
            review_status="returned",
            updated_status=case.status,
            message="Case returned to analyst",
            next_recommended_item_id=_next_recommended_item_id(
                kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
            ),
        )

    if kind == "approval":
        decision = _resolve_approval(item_id, db, current_user)
        parent_case = _resolve_case(str(decision.case_id), db, current_user)
        approval_queue_item = _approval_queue_item(decision, {parent_case.id: parent_case}, now)
        approval_ai_recommendation = AiRecommendation(
            summary="Validate rationale and enforce 4-eyes policy before approval.",
            confidence=0.88,
            rationale=["approval_queue", "maker_checker_required"],
        )
        if payload.decision == "approve" and decision.created_by == current_user.user_id:
            raise HTTPException(
                status_code=409,
                detail="4-eyes violation: approver cannot be the same as submitter",
            )
        if payload.decision == "approve":
            decision.status = "approved"
            decision.approver_id = current_user.user_id
            decision.approved_at = now
            _record_dashboard_work_item_event(
                db=db,
                current_user=current_user,
                entity_type="case_decision",
                entity_id=str(decision.id),
                event_type="dashboard.approval.review.approved",
                payload={
                    "actor_id": current_user.user_id,
                    "decision": payload.decision,
                    "status": decision.status,
                    "maker_user_id": decision.created_by,
                    "notes": payload.review_notes,
                    "decision_trace": _decision_trace_payload(
                        _build_decision_trace(
                            queue_item=approval_queue_item,
                            ai_recommendation=approval_ai_recommendation,
                            human_decision=payload.decision,
                            override_reason=payload.review_notes,
                        )
                    ),
                },
            )
            db.commit()
            return ReviewActionResponse(
                success=True,
                review_status="approved",
                updated_status=decision.status,
                message="Decision approved",
                next_recommended_item_id=_next_recommended_item_id(
                    kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
                ),
            )

        decision.status = "rejected"
        decision.rejection_reason = payload.review_notes
        decision.approver_id = current_user.user_id
        decision.approved_at = now
        _record_dashboard_work_item_event(
            db=db,
            current_user=current_user,
            entity_type="case_decision",
            entity_id=str(decision.id),
            event_type="dashboard.approval.review.returned",
            payload={
                "actor_id": current_user.user_id,
                "decision": payload.decision,
                "status": decision.status,
                "maker_user_id": decision.created_by,
                "notes": payload.review_notes,
                "decision_trace": _decision_trace_payload(
                    _build_decision_trace(
                        queue_item=approval_queue_item,
                        ai_recommendation=approval_ai_recommendation,
                        human_decision=payload.decision,
                        override_reason=payload.review_notes,
                    )
                ),
            },
        )
        db.commit()
        return ReviewActionResponse(
            success=True,
            review_status="returned",
            updated_status=decision.status,
            message="Decision returned to submitter",
            next_recommended_item_id=_next_recommended_item_id(
                kind=kind, item_id=item_id, db=db, current_user=current_user, now=now
            ),
        )

    raise HTTPException(status_code=400, detail="Unsupported work item kind")

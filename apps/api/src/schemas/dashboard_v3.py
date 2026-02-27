"""Schemas for AMLCO Command Center v3 endpoints."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


WorkItemKind = Literal["alert", "case", "approval", "reg_task"]
SlaStatus = Literal["breached", "warning", "ok", "none"]
DashboardQueueFilter = Literal["all", "alerts", "cases", "approvals", "reg_tasks"]
DashboardSeverityFilter = Literal["all", "low", "medium", "high", "critical"]
DashboardSavedViewPreset = Literal["all", "my_queue", "team_queue", "escalations"]
DashboardRole = Literal["analyst", "reviewer", "manager", "qa_audit"]
DashboardSavedViewScope = Literal["private", "team"]
QueueDensity = Literal["comfortable", "compact"]


class CriticalDecisionBar(BaseModel):
    p1_sla_breaches: int = 0
    p2_sla_breaches: int = 0
    sanctions_hits_unreviewed: int = 0
    sar_due_24h: int = 0
    high_risk_cases_unassigned: int = 0
    ingestion_lag_minutes: int = 0


class QueueSummary(BaseModel):
    alerts_open: int = 0
    cases_open: int = 0
    approvals_pending: int = 0
    reg_tasks_due: int = 0


class GovernanceSnapshot(BaseModel):
    rule_drift_score: float = 0.0
    alert_to_case_rate: float = 0.0
    fp_proxy_rate: float = 0.0
    audit_completeness_rate: float = 0.0
    rule_drift_score_history: list[float] | None = None
    alert_to_case_rate_history: list[float] | None = None
    fp_proxy_rate_history: list[float] | None = None
    audit_completeness_rate_history: list[float] | None = None


class ThroughputSnapshot(BaseModel):
    median_time_to_first_action_minutes: float = 0.0
    median_case_resolution_hours: float = 0.0
    median_time_to_first_action_delta_minutes: float | None = None
    median_case_resolution_delta_hours: float | None = None
    median_time_to_first_action_history: list[float] | None = None
    median_case_resolution_history: list[float] | None = None


class FreshnessMeta(BaseModel):
    generated_at: datetime
    stale_after_seconds: int
    source_watermark_at: datetime | None = None
    source_lag_seconds: int | None = None


class ReviewRequirement(BaseModel):
    required: bool = False
    reasons: list[str] = Field(default_factory=list)


class DashboardWorkQueueItem(BaseModel):
    item_id: str
    record_id: str
    kind: WorkItemKind
    ref_id: str
    type_label: str
    severity: str
    entity: str
    entity_type: str | None = None
    typology: str
    jurisdiction: str
    age_minutes: int
    sla_due_at: datetime | None = None
    sla_status: SlaStatus = "none"
    owner: str | None = None
    next_action: str
    risk_score: float = 0.0
    status: str
    sar_required: bool = False
    review_requirement: ReviewRequirement = Field(default_factory=ReviewRequirement)


class DashboardWorkQueueResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[DashboardWorkQueueItem]
    freshness: FreshnessMeta | None = None


class WorkItemTimelineEvent(BaseModel):
    at: datetime
    label: str
    detail: str | None = None


class AiRecommendation(BaseModel):
    summary: str
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)


class EvidenceChecklistItem(BaseModel):
    id: str
    label: str
    completed: bool = False


class ActionHistoryItem(BaseModel):
    at: datetime
    actor: str
    action: str
    notes: str | None = None


class ReviewProvenance(BaseModel):
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_outcome: Literal["approved", "returned"] | None = None
    return_reason: str | None = None


class DecisionTrace(BaseModel):
    facts_used: list[str] = Field(default_factory=list)
    policy_rules_triggered: list[str] = Field(default_factory=list)
    ai_summary: str | None = None
    ai_confidence: float | None = None
    human_decision: str | None = None
    override_reason: str | None = None


class WorkItemDetailResponse(BaseModel):
    work_item: DashboardWorkQueueItem
    context_timeline: list[WorkItemTimelineEvent] = Field(default_factory=list)
    linked_entities: list[str] = Field(default_factory=list)
    linked_transactions: list[str] = Field(default_factory=list)
    ai_recommendation: AiRecommendation
    narrative: str = ""
    evidence_checklist: list[EvidenceChecklistItem] = Field(default_factory=list)
    action_history: list[ActionHistoryItem] = Field(default_factory=list)
    review_requirement: ReviewRequirement = Field(default_factory=ReviewRequirement)
    allowed_actions: list[str] = Field(default_factory=list)
    freshness: FreshnessMeta | None = None
    review_provenance: ReviewProvenance | None = None
    decision_trace: DecisionTrace | None = None


class WorkItemActionRequest(BaseModel):
    action: Literal[
        "assign",
        "escalate",
        "mark_in_progress",
        "create_case",
        "close",
    ]
    assignee: str | None = None
    notes: str | None = None
    sar_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkItemActionResponse(BaseModel):
    success: bool
    message: str
    updated_status: str
    created_case_id: str | None = None
    next_recommended_item_id: str | None = None


class ReviewActionRequest(BaseModel):
    proposed_action: Literal["close", "approve"] = "close"
    decision: Literal["approve", "return"]
    submitted_by: str
    review_notes: str | None = None
    sar_required: bool = False


class ReviewActionResponse(BaseModel):
    success: bool
    review_status: Literal["approved", "returned"]
    updated_status: str
    message: str
    next_recommended_item_id: str | None = None


class WorkItemDraftUpdateRequest(BaseModel):
    narrative: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkItemDraftUpdateResponse(BaseModel):
    success: bool
    message: str
    updated_at: datetime


class WorkspaceUser(BaseModel):
    user_id: str
    role: str
    is_active: bool


class DashboardSavedViewFilters(BaseModel):
    page: int = 1
    pageSize: int = 50
    queue: DashboardQueueFilter = "all"
    severity: DashboardSeverityFilter = "all"
    jurisdiction: str = ""
    sla: Literal["all", "breached", "warning", "ok", "none"] = "all"
    search: str = ""
    savedView: DashboardSavedViewPreset = "all"


class DashboardLayoutPreferences(BaseModel):
    queueDensity: QueueDensity | None = None
    insightsOpen: bool | None = None
    defaultWorkspaceTab: str | None = None


class DashboardSavedViewRecord(BaseModel):
    id: str
    name: str
    scope: DashboardSavedViewScope
    owner_user_id: str
    team_id: str | None = None
    is_default_for_role: bool = False
    role: DashboardRole | None = None
    filters: DashboardSavedViewFilters
    layout_prefs: DashboardLayoutPreferences | None = None
    created_at: datetime
    updated_at: datetime
    updated_by_user_id: str | None = None


class DashboardSavedViewsResponse(BaseModel):
    items: list[DashboardSavedViewRecord] = Field(default_factory=list)
    resolved_default_view_id: str | None = None


class DashboardSavedViewCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scope: DashboardSavedViewScope = "private"
    is_default_for_role: bool = False
    role: DashboardRole | None = None
    filters: DashboardSavedViewFilters
    layout_prefs: DashboardLayoutPreferences | None = None


class DashboardSavedViewUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    scope: DashboardSavedViewScope | None = None
    is_default_for_role: bool | None = None
    role: DashboardRole | None = None
    filters: DashboardSavedViewFilters | None = None
    layout_prefs: DashboardLayoutPreferences | None = None


class DashboardPreferencesResponse(BaseModel):
    layout_prefs: DashboardLayoutPreferences = Field(default_factory=DashboardLayoutPreferences)
    default_saved_view_id: str | None = None
    updated_at: datetime | None = None


class DashboardPreferencesUpdateRequest(BaseModel):
    layout_prefs: DashboardLayoutPreferences | None = None
    default_saved_view_id: str | None = None

export type DashboardView = "operations" | "compliance" | "monitoring";
export type DashboardTimeRange = "24h" | "7d" | "30d";
export type DashboardQueueFilter =
  | "all"
  | "alerts"
  | "cases"
  | "approvals"
  | "reg_tasks";
export type DashboardSeverityFilter =
  | "all"
  | "low"
  | "medium"
  | "high"
  | "critical";
export type DashboardSlaFilter = "all" | "breached" | "warning" | "ok" | "none";
export type DashboardSavedView =
  | "all"
  | "my_queue"
  | "team_queue"
  | "escalations";
export type WorkItemKind = "alert" | "case" | "approval" | "reg_task";

export interface DashboardKpis {
  pending_alerts: number;
  critical_alerts: number;
  open_cases: number;
  transactions_in_range: number;
  average_risk_score: number;
}

export interface AlertQueueItem {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: "low" | "medium" | "high" | "critical";
  status: string;
  priority: number;
  user_id: string;
  risk_score: number;
  created_at: string | null;
}

export interface CaseQueueItem {
  id: number;
  case_id: string;
  title: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  opened_at: string | null;
  updated_at: string | null;
}

export interface SystemHealthSnapshot {
  status: "healthy" | "warning" | "degraded" | string;
  stuck_alerts: number;
  unprocessed_transactions: number;
}

export interface DashboardFreshnessMeta {
  generated_at: string;
  stale_after_seconds: number;
  source_watermark_at?: string | null;
  source_lag_seconds?: number | null;
}

export interface CriticalDecisionBar {
  p1_sla_breaches: number;
  p2_sla_breaches: number;
  sanctions_hits_unreviewed: number;
  sar_due_24h: number;
  high_risk_cases_unassigned: number;
  ingestion_lag_minutes: number;
}

export interface DashboardQueueSummary {
  alerts_open: number;
  cases_open: number;
  approvals_pending: number;
  reg_tasks_due: number;
}

export interface DashboardGovernanceSnapshot {
  rule_drift_score: number;
  alert_to_case_rate: number;
  fp_proxy_rate: number;
  audit_completeness_rate: number;
  rule_drift_score_history?: number[] | null;
  alert_to_case_rate_history?: number[] | null;
  fp_proxy_rate_history?: number[] | null;
  audit_completeness_rate_history?: number[] | null;
}

export interface DashboardThroughputSnapshot {
  median_time_to_first_action_minutes: number;
  median_case_resolution_hours: number;
  median_time_to_first_action_delta_minutes?: number | null;
  median_case_resolution_delta_hours?: number | null;
  median_time_to_first_action_history?: number[] | null;
  median_case_resolution_history?: number[] | null;
}

export interface DashboardOverviewResponse {
  view: DashboardView;
  time_range: DashboardTimeRange;
  generated_at: string;
  kpis: DashboardKpis;
  badges: {
    alerts_pending: number;
    cases_open: number;
    critical_open: number;
  };
  system_health: SystemHealthSnapshot;
  queues: {
    alerts: AlertQueueItem[];
    cases: CaseQueueItem[];
  };
  critical_bar: CriticalDecisionBar;
  queue_summary: DashboardQueueSummary;
  governance: DashboardGovernanceSnapshot;
  throughput: DashboardThroughputSnapshot;
  queue_summary_previous?: DashboardQueueSummary | null;
  critical_bar_previous?: CriticalDecisionBar | null;
  freshness?: DashboardFreshnessMeta | null;
}

export type WorkItemSlaStatus = "breached" | "warning" | "ok" | "none";

export interface ReviewRequirement {
  required: boolean;
  reasons: string[];
}

export interface DashboardWorkQueueItem {
  item_id: string;
  record_id: string;
  kind: WorkItemKind;
  ref_id: string;
  type_label: string;
  severity: string;
  entity: string;
  entity_type?: string | null;
  typology: string;
  jurisdiction: string;
  age_minutes: number;
  sla_due_at: string | null;
  sla_status: WorkItemSlaStatus;
  owner: string | null;
  next_action: string;
  risk_score: number;
  status: string;
  sar_required: boolean;
  review_requirement: ReviewRequirement;
}

export interface DashboardWorkQueueResponse {
  page: number;
  page_size: number;
  total: number;
  items: DashboardWorkQueueItem[];
  freshness?: DashboardFreshnessMeta | null;
}

export interface WorkItemTimelineEvent {
  at: string;
  label: string;
  detail: string | null;
}

export interface WorkItemAiRecommendation {
  summary: string;
  confidence: number;
  rationale: string[];
}

export interface WorkItemEvidenceChecklistItem {
  id: string;
  label: string;
  completed: boolean;
}

export interface WorkItemActionHistoryItem {
  at: string;
  actor: string;
  action: string;
  notes: string | null;
}

export interface ReviewProvenance {
  submitted_by?: string | null;
  submitted_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_outcome?: "approved" | "returned" | null;
  return_reason?: string | null;
}

export interface DecisionTrace {
  facts_used?: string[];
  policy_rules_triggered?: string[];
  ai_summary?: string | null;
  ai_confidence?: number | null;
  human_decision?: string | null;
  override_reason?: string | null;
}

export interface WorkItemDetailResponse {
  work_item: DashboardWorkQueueItem;
  context_timeline: WorkItemTimelineEvent[];
  linked_entities: string[];
  linked_transactions: string[];
  ai_recommendation: WorkItemAiRecommendation;
  narrative: string;
  evidence_checklist: WorkItemEvidenceChecklistItem[];
  action_history: WorkItemActionHistoryItem[];
  review_requirement: ReviewRequirement;
  allowed_actions: WorkItemActionType[];
  freshness?: DashboardFreshnessMeta | null;
  review_provenance?: ReviewProvenance | null;
  decision_trace?: DecisionTrace | null;
}

export type WorkItemActionType =
  | "assign"
  | "escalate"
  | "mark_in_progress"
  | "create_case"
  | "close";

export interface WorkItemActionRequest {
  action: WorkItemActionType;
  assignee?: string;
  notes?: string;
  sar_required?: boolean;
  metadata?: Record<string, unknown>;
}

export interface WorkItemActionResponse {
  success: boolean;
  message: string;
  updated_status: string;
  created_case_id?: string | null;
  next_recommended_item_id?: string | null;
}

export interface ReviewActionRequest {
  proposed_action: "close" | "approve";
  decision: "approve" | "return";
  submitted_by: string;
  review_notes?: string;
  sar_required?: boolean;
}

export interface ReviewActionResponse {
  success: boolean;
  review_status: "approved" | "returned";
  updated_status: string;
  message: string;
  next_recommended_item_id?: string | null;
}

export interface DashboardWorkQueueParams {
  page: number;
  pageSize: number;
  queue: DashboardQueueFilter;
  severity: DashboardSeverityFilter;
  jurisdiction: string;
  sla: DashboardSlaFilter;
  search: string;
  savedView: DashboardSavedView;
}

export interface WorkspaceMessage {
  text: string;
  type: "success" | "warning" | "error";
}

export type DashboardSavedViewScope = "private" | "team";
export type DashboardSavedViewRole =
  | "analyst"
  | "reviewer"
  | "manager"
  | "qa_audit";
export type DashboardQueueDensityPreference = "comfortable" | "compact";

export interface DashboardLayoutPreferences {
  queueDensity?: DashboardQueueDensityPreference | null;
  insightsOpen?: boolean | null;
  defaultWorkspaceTab?: string | null;
}

export interface DashboardSavedViewRecord {
  id: string;
  name: string;
  scope: DashboardSavedViewScope;
  owner_user_id: string;
  team_id?: string | null;
  is_default_for_role?: boolean;
  role?: DashboardSavedViewRole | null;
  filters: DashboardWorkQueueParams;
  layout_prefs?: DashboardLayoutPreferences | null;
  created_at: string;
  updated_at: string;
  updated_by_user_id?: string | null;
}

export interface DashboardSavedViewsResponse {
  items: DashboardSavedViewRecord[];
  resolved_default_view_id?: string | null;
}

export interface DashboardPreferencesResponse {
  layout_prefs: DashboardLayoutPreferences;
  default_saved_view_id?: string | null;
  updated_at?: string | null;
}

export interface DashboardSavedViewCreateRequest {
  name: string;
  scope: DashboardSavedViewScope;
  is_default_for_role?: boolean;
  role?: DashboardSavedViewRole | null;
  filters: DashboardWorkQueueParams;
  layout_prefs?: DashboardLayoutPreferences | null;
}

export interface DashboardSavedViewUpdateRequest {
  name?: string;
  scope?: DashboardSavedViewScope;
  is_default_for_role?: boolean;
  role?: DashboardSavedViewRole | null;
  filters?: DashboardWorkQueueParams;
  layout_prefs?: DashboardLayoutPreferences | null;
}

export interface DashboardPreferencesUpdateRequest {
  layout_prefs?: DashboardLayoutPreferences;
  default_saved_view_id?: string | null;
}

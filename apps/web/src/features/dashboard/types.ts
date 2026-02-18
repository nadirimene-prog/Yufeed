export type DashboardView = "operations" | "compliance" | "monitoring";
export type DashboardTimeRange = "24h" | "7d" | "30d";

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
  severity: "low" | "medium" | "high" | "critical" | string;
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
}

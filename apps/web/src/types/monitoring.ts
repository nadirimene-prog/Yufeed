export interface MonitoringAlert {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: string;
  user_id: string;
  status: string;
  priority: number;
  description: string;
  risk_score: number;
  created_at: string;
  assigned_to?: string;
  ai_recommendation?: string;
  ai_confidence?: number;
}

export interface MonitoringCase {
  id: number;
  case_id: string;
  case_type: string;
  status: string;
  severity: string;
  subject_type?: string;
  subject_id?: string;
  description?: string;
  summary?: string;
  opened_at: string;
  closed_at?: string;
  assigned_to?: string;
  escalated_to?: string;
  outcome?: string;
  related_alert_ids?: number[];
  related_transaction_ids?: number[];
}


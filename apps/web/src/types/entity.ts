import type { MonitoringCase } from "@/types/monitoring";

export type EntityType = "user" | "kyc_profile" | "transaction" | "entity";

export interface EntityRiskProfile {
  overall_score: number;
  risk_level: string;
  kyc_status: string;
  enhanced_due_diligence: boolean;
  last_updated: string | null;
}

export interface EntityComplianceProfile {
  id: number;
  status: string;
  risk_level: string;
  type: string;
  updated_at: string | null;
}

export interface EntityAlert {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: string;
  status: string;
  priority: number;
  risk_score: number;
  created_at: string | null;
  assigned_to?: string | null;
  triggered_rule_id?: string;
  triggered_rule_name?: string;
}

export interface EntityTransaction {
  id: number;
  transaction_id: string;
  amount: number;
  currency: string;
  transaction_type: string;
  timestamp: string | null;
  status: string;
  country_code: string | null;
  risk_score: number;
}

export interface EntityNetworkSummary {
  seed_user_id: string | null;
  alerts_count: number;
  cases_count: number;
  transactions_count: number;
}

export interface EntityProfile {
  type: EntityType;
  id: string;
  user_id: string | null;
  risk: EntityRiskProfile | null;
  compliance: EntityComplianceProfile | null;
  alerts: EntityAlert[];
  cases: MonitoringCase[];
  transactions: EntityTransaction[];
  network: EntityNetworkSummary;
}

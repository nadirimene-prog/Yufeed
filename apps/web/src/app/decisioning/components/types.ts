export type DecisionResponse = {
  event_id: string;
  decision_id: string;
  decision: string;
  risk_score?: number | null;
  risk_level?: string | null;
  alerts: string[];
  reason_codes: string[];
  evidence: Record<string, unknown>;
};

export type DecisionListItem = {
  decision_id: string;
  event_id?: string | null;
  decision: string;
  reason_codes?: string[] | null;
  rule_version?: string | null;
  model_version?: string | null;
  created_at: string;
  event_type?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  source?: string | null;
};

export type DecisionEvidenceBundle = {
  export_id: string;
  exported_at: string;
  decision: Record<string, unknown> & {
    evidence?: {
      risk_score?: number | string | null;
      risk_level?: string | null;
      alerts?: unknown[] | null;
      onchain?: { risk_level?: string | null } | null;
    };
  };
  event?: {
    event_type?: string | null;
    entity_type?: string | null;
    entity_id?: string | null;
    source?: string | null;
    payload?: Record<string, unknown> | null;
    metadata?: (Record<string, unknown> & { context?: Record<string, unknown> }) | null;
  } | null;
  transaction?: Record<string, unknown> | null;
  alerts: Record<string, unknown>[];
  audit_logs: Record<string, unknown>[];
};

export type DecisionListResponse = {
  total: number;
  items: DecisionListItem[];
};

export type EventResponse = {
  event_id: string;
  event_type: string;
  entity_type?: string | null;
  entity_id?: string | null;
  metadata: Record<string, unknown>;
};

export type FeatureSetResponse = {
  entity_type: string;
  entity_id: string;
  features: Record<string, unknown>;
};

export type TransactionResponse = {
  id: number;
  transaction_id: string;
  user_id: string;
  amount: number;
  currency: string;
  transaction_type?: string | null;
};

export type ReplayDiffRow = {
  label: string;
  original: string;
  replay: string;
};


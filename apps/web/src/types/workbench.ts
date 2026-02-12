// Finding types
export type FindingSeverity = "critical" | "high" | "medium" | "low" | "info";
export type FindingStatus = "open" | "acknowledged" | "escalated" | "closed";
export type FindingType =
  | "aml"
  | "kyc"
  | "sanctions"
  | "fraud"
  | "regulatory"
  | "operational";

export interface Finding {
  id: number;
  tenant_id: string;
  fingerprint: string;
  finding_type: FindingType;
  severity: FindingSeverity;
  status: FindingStatus;
  title: string;
  summary: string;
  source_refs: Record<string, unknown>;
  explainability: Record<string, unknown>;
  assigned_to?: string;
  sla_due_at?: string;
  closed_reason?: string;
  closed_comment?: string;
  created_at: string;
  updated_at: string;
}

// Case Decision types
export type DecisionStatus = "draft" | "submitted" | "approved" | "rejected";
export type DispositionType =
  | "escalate"
  | "close_no_action"
  | "close_with_sar"
  | "refer_external";

export interface CaseDecision {
  id: number;
  tenant_id: string;
  case_id: string;
  version: number;
  status: DecisionStatus;
  disposition: DispositionType;
  rationale: string;
  created_by: string;
  submitted_at?: string;
  approver_id?: string;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

// Evidence Pack types
export type EvidenceFormat = "json" | "pdf" | "zip";

export interface EvidencePack {
  id: number;
  pack_id: string;
  case_id: string;
  schema_version: string;
  version: number;
  format: EvidenceFormat;
  integrity_hash: string;
  storage_ref: string;
  created_by: string;
  created_at: string;
}

export interface EvidencePackDetail extends EvidencePack {
  snapshot: Record<string, unknown>;
}

// List params
export interface FindingListParams {
  limit?: number;
  status?: string;
  severity?: string;
  finding_type?: string;
  assigned_to?: string;
}

export interface DecisionListParams {
  limit?: number;
  status?: string;
}

export interface EvidencePackListParams {
  limit?: number;
}

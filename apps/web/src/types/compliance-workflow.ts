import type { PolicySection } from "@/types/compliance";

export interface InternalRuleMonitoringRule {
  id: number;
  rule_id: string;
  name: string;
  severity?: string | null;
  enabled?: boolean | null;
}

export interface InternalRuleMapping {
  id: number;
  internal_rule_id: number;
  monitoring_rule_id?: number | null;
  mapping_type?: string | null;
  created_at?: string | null;
  monitoring_rule?: InternalRuleMonitoringRule | null;
}

export interface InternalRule {
  id: number;
  internal_rule_id: string;
  obligation_id: number;
  policy_section_id?: number | null;
  name: string;
  description?: string | null;
  control_owner?: string | null;
  status?: string | null;
  reviewed_by?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  updated_at?: string | null;
  policy_section?: PolicySection | null;
  mappings?: InternalRuleMapping[];
}

export interface InternalRuleCreatePayload {
  internal_rule_id?: string;
  policy_section_id?: number;
  name: string;
  description?: string;
  control_owner?: string;
  status?: string;
}

export interface InternalRuleMappingCreatePayload {
  monitoring_rule_id?: number;
  monitoring_rule_rule_id?: string;
  mapping_type?: string;
}


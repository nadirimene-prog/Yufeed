import type { PolicySection } from "@/types/compliance";

export interface InternalRuleMapping {
  id: number;
  internal_rule_id: number;
  monitoring_rule_id?: number | null;
  mapping_type?: string | null;
  monitoring_rule?: {
    id: number;
    rule_id: string;
    name: string;
    severity?: string | null;
    enabled?: boolean | null;
  } | null;
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
  policy_section?: PolicySection | null;
  mappings?: InternalRuleMapping[];
}


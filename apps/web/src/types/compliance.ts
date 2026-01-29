export type ComplianceStatus = "pending" | "approved" | "rejected" | "manual_review";
export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface ComplianceDocument {
    id: number;
    document_type: string;
    file_url: string;
    verification_status: string;
    uploaded_at: string;
}

export interface RiskSignal {
    id: number;
    signal_type: string;
    score: number;
    description?: string;
    detected_at: string;
}

export interface ComplianceProfile {
    id: number;
    status: ComplianceStatus;
    risk_level: RiskLevel;
    created_at: string;
    updated_at: string;
    type: "kyc" | "kyb";
    documents: ComplianceDocument[];
    risk_signals: RiskSignal[];

    // KYC Fields
    first_name?: string;
    last_name?: string;
    email?: string;
    phone_number?: string;
    date_of_birth?: string;
    address_line1?: string;
    city?: string;
    country?: string;

    // KYB Fields
    company_name?: string;
    registration_number?: string;
    jurisdiction?: string;
    website?: string;
    industry?: string;
}

export interface ComplianceMetrics {
    total_pending: number;
    high_risk_count: number;
    approved_today: number;
}

// ========== Policy Types ==========

export type PolicyStatus = "draft" | "in_review" | "approved" | "active" | "retired";

export interface Policy {
    id: number;
    policy_id: string;
    name: string;
    version?: string;
    owner?: string;
    status: PolicyStatus;
    language: string;
    effective_date?: string;
    last_reviewed_at?: string;
    source_url?: string;
    content?: string;
    metadata?: Record<string, unknown>;
    created_at: string;
    updated_at?: string;
    sections_count?: number;
    linked_obligations_count?: number;
}

export interface PolicySection {
    id: number;
    policy_id: number;
    section_ref?: string;
    title?: string;
    content?: string;
    status: string;
    version?: string;
    last_reviewed_at?: string;
    created_at: string;
    updated_at?: string;
}

export interface PolicyCreate {
    name: string;
    version?: string;
    owner?: string;
    status?: PolicyStatus;
    language?: string;
    effective_date?: string;
    source_url?: string;
    content?: string;
    metadata?: Record<string, unknown>;
}

export interface PolicyUpdate {
    name?: string;
    version?: string;
    owner?: string;
    status?: PolicyStatus;
    language?: string;
    effective_date?: string;
    source_url?: string;
    content?: string;
    metadata?: Record<string, unknown>;
}

// ========== Risk Types ==========

export type RiskLevelType = "low" | "medium" | "high" | "critical";
export type LikelihoodLevel = "rare" | "unlikely" | "possible" | "likely" | "almost_certain";
export type ImpactLevel = "insignificant" | "minor" | "moderate" | "major" | "catastrophic";
export type MitigationStatus = "not_started" | "in_progress" | "implemented" | "monitored";
export type LinkType = "mitigates" | "addresses" | "monitors";

export interface RiskCategory {
    id: number;
    category_id: string;
    name: string;
    description?: string;
    parent_id?: number;
    risk_level: RiskLevelType;
    status: "active" | "inactive";
    created_at: string;
    updated_at?: string;
    children_count?: number;
    entries_count?: number;
}

export interface RiskCategoryTree extends RiskCategory {
    children: RiskCategoryTree[];
}

export interface RiskEntry {
    id: number;
    risk_id: string;
    category_id: number;
    category_name?: string;
    name: string;
    description?: string;
    inherent_risk_level: RiskLevelType;
    residual_risk_level: RiskLevelType;
    likelihood?: LikelihoodLevel;
    impact?: ImpactLevel;
    mitigation_status: MitigationStatus;
    control_owner?: string;
    review_date?: string;
    metadata?: Record<string, unknown>;
    created_at: string;
    updated_at?: string;
    linked_obligations_count?: number;
}

export interface RiskEntryCreate {
    category_id: number;
    name: string;
    description?: string;
    inherent_risk_level?: RiskLevelType;
    residual_risk_level?: RiskLevelType;
    likelihood?: LikelihoodLevel;
    impact?: ImpactLevel;
    mitigation_status?: MitigationStatus;
    control_owner?: string;
    review_date?: string;
    metadata?: Record<string, unknown>;
}

export interface RiskEntryUpdate {
    category_id?: number;
    name?: string;
    description?: string;
    inherent_risk_level?: RiskLevelType;
    residual_risk_level?: RiskLevelType;
    likelihood?: LikelihoodLevel;
    impact?: ImpactLevel;
    mitigation_status?: MitigationStatus;
    control_owner?: string;
    review_date?: string;
    metadata?: Record<string, unknown>;
}

export interface ObligationRiskLink {
    id: number;
    obligation_id: number;
    risk_entry_id: number;
    link_type: LinkType;
    notes?: string;
    created_by?: string;
    created_at: string;
    obligation_text?: string;
    obligation_article_ref?: string;
}

export interface RiskMapSummary {
    total_categories: number;
    total_entries: number;
    by_inherent_level: Record<RiskLevelType, number>;
    by_residual_level: Record<RiskLevelType, number>;
    by_mitigation_status: Record<MitigationStatus, number>;
    by_category: Array<{
        id: number;
        category_id: string;
        name: string;
        entries_count: number;
    }>;
    high_priority_risks: RiskEntry[];
}

export interface RiskHeatMapCell {
    likelihood: LikelihoodLevel;
    impact: ImpactLevel;
    count: number;
    risk_ids: string[];
}

export interface RiskHeatMapData {
    cells: RiskHeatMapCell[];
    total_risks: number;
}

// ========== Obligation Types ==========

export type ObligationStatus = "draft" | "in_review" | "approved" | "rejected" | "deprecated";

export interface Obligation {
    id: number;
    obligation_id: string;
    status: ObligationStatus;
    article_ref?: string;
    obligation_text: string;
    applicability?: string;
    effective_date?: string;
    created_by?: string;
    reviewed_by?: string;
    approved_by?: string;
    approved_at?: string;
    review_notes?: string;
    updated_at?: string;
    scope_tags?: string[];
    tags?: Record<string, unknown>;
    evidence?: Record<string, unknown>;
    linked_policy_id?: number;
    linked_policy?: {
        id: number;
        policy_id: string;
        name: string;
        status: string;
    };
    linked_risks_count?: number;
    internal_rules_count?: number;
    linked_risks?: Array<{
        link_id: number;
        link_type: LinkType;
        risk_id: string;
        name: string;
        inherent_risk_level: RiskLevelType;
        residual_risk_level: RiskLevelType;
    }>;
    internal_rules?: Array<{
        id: number;
        internal_rule_id: string;
        name: string;
        status: string;
        control_owner?: string;
    }>;
    document: {
        id: number;
        celex?: string;
        title: string;
        jurisdiction?: string;
        source_system?: string;
        publication_date?: string;
        scope_tags?: string[];
    };
}

export interface ObligationApprovalData {
    status: ObligationStatus;
    note?: string;
    linked_policy_id?: number;
    create_internal_rule?: boolean;
    internal_rule_name?: string;
    internal_rule_description?: string;
    link_risk_entry_ids?: number[];
}

export interface InternalRule {
    id: number;
    internal_rule_id: string;
    name: string;
    description?: string;
    status: string;
    control_owner?: string;
    policy_section_id?: number;
    created_at: string;
    updated_at?: string;
}

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

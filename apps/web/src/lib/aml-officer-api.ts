/**
 * AI AML Officer API Client
 *
 * Client for interacting with the AI AML Officer backend endpoints.
 * Provides methods for:
 * - Alert investigation
 * - Daily briefings
 * - Compliance Q&A
 * - Sanctions screening
 * - SAR preparation
 */

import apiClient from "./http";

// =============================================================================
// TYPES
// =============================================================================

export interface InvestigationRequest {
  alert_id: number;
  alert_data: Record<string, unknown>;
  related_transactions?: Record<string, unknown>[];
  related_regulations?: Record<string, unknown>[];
  user_id?: string;
}

export interface InvestigationResult {
  success: boolean;
  alert_id?: number;
  recommendation?: string;
  confidence: number;
  confidence_level: "high" | "medium" | "low";
  summary: string;
  detailed_analysis: string;
  risk_score?: number;
  risk_factors: string[];
  red_flags: string[];
  mitigating_factors: string[];
  citations: Citation[];
  next_steps: string[];
  sar_likelihood?: number;
  processing_time_ms: number;
  error_message?: string;
}

export interface Citation {
  source_type: string;
  reference: string;
  celex_id?: string;
  excerpt?: string;
  relevance_score: number;
}

export interface DailyBriefing {
  briefing_id: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  alerts: {
    new: number;
    critical: number;
    pending: number;
    auto_resolved: number;
  };
  cases: {
    open: number;
    requiring_action: number;
    sar_pending: number;
  };
  risk: {
    high_risk_users: HighRiskUser[];
    emerging_patterns: string[];
    trend: "increasing" | "stable" | "decreasing";
  };
  regulatory: {
    new_regulations: Regulation[];
    upcoming_deadlines: Deadline[];
  };
  recommendations: {
    priority_actions: string[];
    focus_areas: string[];
  };
  narrative: {
    executive_summary: string;
    detailed_analysis: string;
  };
}

export interface HighRiskUser {
  user_id: string;
  risk_score: number;
  reason: string;
}

export interface Regulation {
  celex_id: string;
  title: string;
  published_at: string;
}

export interface Deadline {
  title: string;
  date: string;
  days_remaining: number;
}

export interface ComplianceQuestion {
  question: string;
  context?: Record<string, unknown>;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface ComplianceAnswer {
  answer: string;
  confidence: "high" | "medium" | "low";
  sources: Source[];
  followup_questions: string[];
}

export interface Source {
  celex_id: string;
  title: string;
  relevance_score: number;
}

export interface SanctionsScreenRequest {
  name: string;
  entity_type?: string;
  nationality?: string;
  birth_date?: string;
  lists?: string[];
}

export interface SanctionsScreenResult {
  screened_name: string;
  screened_at: string;
  is_hit: boolean;
  match_count: number;
  highest_score: number;
  matches: SanctionsMatch[];
  lists_checked: string[];
  processing_time_ms: number;
}

export interface SanctionsMatch {
  list_type: string;
  entity_type: string;
  match_type: string;
  matched_name: string;
  original_name: string;
  score: number;
  sanctions_id: string;
  aliases: string[];
  nationalities: string[];
  programs: string[];
  reasons: string[];
}

export interface ProactiveAlert {
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  message: string;
  recommendation: string;
  detected_at: string;
}

export interface AMLOfficerCapabilities {
  agents: Array<{
    type: string;
    status: "active" | "coming_soon" | "planned";
    description: string;
  }>;
  integrations: Array<{
    name: string;
    status: "active" | "inactive";
  }>;
  features: Record<string, boolean>;
}

// =============================================================================
// API CLIENT
// =============================================================================

export const amlOfficerApi = {
  // -------------------------------------------------------------------------
  // Investigation
  // -------------------------------------------------------------------------

  /**
   * Investigate a single alert
   */
  async investigateAlert(
    request: InvestigationRequest
  ): Promise<InvestigationResult> {
    const response = await apiClient.post<InvestigationResult>(
      `/api/aml-officer/investigate`,
      request
    );
    return response.data;
  },

  /**
   * Investigate multiple alerts in batch
   */
  async batchInvestigate(
    alerts: Record<string, unknown>[],
    maxConcurrent: number = 5
  ): Promise<{
    total_alerts: number;
    successful: number;
    failed: number;
    results: Array<{
      alert_id: number;
      success: boolean;
      recommendation?: string;
      confidence: number;
      risk_score?: number;
      red_flags: string[];
      error_message?: string;
    }>;
  }> {
    const response = await apiClient.post(
      `/api/aml-officer/investigate/batch`,
      { alerts, max_concurrent: maxConcurrent }
    );
    return response.data;
  },

  // -------------------------------------------------------------------------
  // Daily Briefing
  // -------------------------------------------------------------------------

  /**
   * Get the daily compliance briefing
   */
  async getDailyBriefing(lookbackHours: number = 24): Promise<DailyBriefing> {
    const response = await apiClient.get<DailyBriefing>(
      `/api/aml-officer/briefing/daily`,
      { params: { lookback_hours: lookbackHours } }
    );
    return response.data;
  },

  // -------------------------------------------------------------------------
  // Compliance Q&A
  // -------------------------------------------------------------------------

  /**
   * Ask a compliance question
   */
  async askQuestion(request: ComplianceQuestion): Promise<ComplianceAnswer> {
    const response = await apiClient.post<ComplianceAnswer>(
      `/api/aml-officer/ask`,
      request
    );
    return response.data;
  },

  // -------------------------------------------------------------------------
  // Proactive Alerts
  // -------------------------------------------------------------------------

  /**
   * Get proactive alerts from the AI
   */
  async getProactiveAlerts(): Promise<{
    count: number;
    alerts: ProactiveAlert[];
  }> {
    const response = await apiClient.get(`/api/aml-officer/alerts/proactive`);
    return response.data;
  },

  // -------------------------------------------------------------------------
  // Sanctions Screening
  // -------------------------------------------------------------------------

  /**
   * Screen a name against sanctions lists
   */
  async screenSanctions(
    request: SanctionsScreenRequest
  ): Promise<SanctionsScreenResult> {
    const response = await apiClient.post<SanctionsScreenResult>(
      `/api/aml-officer/sanctions/screen`,
      request
    );
    return response.data;
  },

  /**
   * Batch screen multiple names
   */
  async batchScreenSanctions(
    request: { names: string[]; max_concurrent?: number }
  ): Promise<{
    total_screened: number;
    hits: number;
    clear: number;
    results: SanctionsScreenResult[];
  }> {
    const response = await apiClient.post(
      `/api/aml-officer/sanctions/screen/batch`,
      request
    );
    return response.data;
  },

  /**
   * Get sanctions list statistics
   */
  async getSanctionsStatistics(): Promise<{
    total_entries: number;
    by_list: Record<string, number>;
    last_updated: string;
    status: string;
  }> {
    const response = await apiClient.get(
      `/api/aml-officer/sanctions/statistics`
    );
    return response.data;
  },

  // -------------------------------------------------------------------------
  // SAR Preparation
  // -------------------------------------------------------------------------

  /**
   * Prepare a SAR draft
   */
  async prepareSAR(
    caseId: number,
    caseData: Record<string, unknown>,
    relatedAlerts: Record<string, unknown>[] = [],
    relatedTransactions: Record<string, unknown>[] = []
  ): Promise<{
    success: boolean;
    sar_draft: Record<string, unknown>;
  }> {
    const response = await apiClient.post(`/api/aml-officer/sar/prepare`, {
      case_id: caseId,
      case_data: caseData,
      related_alerts: relatedAlerts,
      related_transactions: relatedTransactions,
    });
    return response.data;
  },

  /**
   * Get available SAR templates
   */
  async getSARTemplates(): Promise<{
    templates: Array<{
      id: string;
      name: string;
      jurisdiction: string;
      description: string;
    }>;
  }> {
    const response = await apiClient.get(`/api/aml-officer/sar/templates`);
    return response.data;
  },

  // -------------------------------------------------------------------------
  // Health & Capabilities
  // -------------------------------------------------------------------------

  /**
   * Check the health of the AI AML Officer
   */
  async healthCheck(): Promise<{
    status: "healthy" | "degraded" | "unhealthy";
    components: Record<string, string>;
    timestamp: string;
  }> {
    const response = await apiClient.get(`/api/aml-officer/health`);
    return response.data;
  },

  /**
   * Get the capabilities of the AI AML Officer
   */
  async getCapabilities(): Promise<AMLOfficerCapabilities> {
    const response = await apiClient.get<AMLOfficerCapabilities>(
      `/api/aml-officer/capabilities`
    );
    return response.data;
  },
};

export default amlOfficerApi;

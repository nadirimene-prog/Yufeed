/**
 * Gap Analysis API Client
 *
 * API endpoints for compliance gap analysis and coverage mapping.
 */
import apiClient from "./http";

// Types
export interface GapDashboard {
  overall_coverage_percentage: number;
  total_obligations: number;
  mapped_obligations: number;
  unmapped_obligations: number;
  coverage_by_category: Record<string, number>;
  critical_gaps_count: number;
  high_gaps_count: number;
  medium_gaps_count: number;
  low_gaps_count: number;
}

export interface Gap {
  obligation_id: string;
  obligation_text: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  deadline_days: number | null;
  deadline_date: string | null;
  related_policies: Array<{
    policy_id: string;
    policy_name: string;
    coverage_level: "partial" | "full";
  }>;
  suggested_templates: string[];
}

export interface GapsListResponse {
  gaps: Gap[];
  total: number;
  offset: number;
  limit: number;
  severity_filter: string | null;
  category_filter: string | null;
}

export interface ObligationCoverage {
  obligation_id: string;
  obligation_text: string;
  is_mapped: boolean;
  mapped_policies: Array<{
    policy_id: string;
    policy_name: string;
    internal_rule_id: string | null;
    coverage_level: string;
  }>;
  coverage_percentage: number;
  gaps: string[];
}

export interface CategoryCoverage {
  category: string;
  display_name: string;
  total_obligations: number;
  mapped_obligations: number;
  coverage_percentage: number;
  trend: "improving" | "stable" | "declining";
}

export interface CoverageTrendPoint {
  date: string;
  overall_coverage: number;
  category_coverage: Record<string, number>;
}

export interface MapObligationRequest {
  obligation_id: string;
  policy_id: string;
  internal_rule_id?: string;
  coverage_level: "partial" | "full";
  notes?: string;
}

// API Functions

/**
 * Get gap analysis dashboard data
 */
export const getGapDashboard = async (): Promise<GapDashboard> => {
  const response = await apiClient.get<GapDashboard>(
    "/api/gap-analysis/dashboard",
  );
  return response.data;
};

/**
 * Get list of compliance gaps with filters
 */
export const getGaps = async (params?: {
  severity?: "critical" | "high" | "medium" | "low";
  category?: string;
  scope?: string[];
  has_deadline?: boolean;
  offset?: number;
  limit?: number;
  sort_by?: "severity" | "deadline" | "category";
}): Promise<GapsListResponse> => {
  const response = await apiClient.get<GapsListResponse>(
    "/api/gap-analysis/gaps",
    {
      params,
    },
  );
  return response.data;
};

/**
 * Map an obligation to a policy
 */
export const mapObligationToPolicy = async (
  data: MapObligationRequest,
): Promise<{ message: string; mapping_id: string }> => {
  const response = await apiClient.post(
    "/api/gap-analysis/map-obligation",
    data,
  );
  return response.data;
};

/**
 * Unmap an obligation from its policies
 */
export const unmapObligation = async (
  obligationId: string,
): Promise<{ message: string }> => {
  const response = await apiClient.post(
    `/api/gap-analysis/unmap-obligation/${obligationId}`,
  );
  return response.data;
};

/**
 * Get coverage details for a specific obligation
 */
export const getObligationCoverage = async (
  obligationId: string,
): Promise<ObligationCoverage> => {
  const response = await apiClient.get<ObligationCoverage>(
    `/api/gap-analysis/obligation/${obligationId}/coverage`,
  );
  return response.data;
};

/**
 * Get coverage breakdown by document
 */
export const getCoverageByDocument = async (): Promise<
  Array<{
    celex: string;
    title: string;
    total_obligations: number;
    mapped_obligations: number;
    coverage_percentage: number;
  }>
> => {
  const response = await apiClient.get(
    "/api/gap-analysis/coverage-by-document",
  );
  return response.data;
};

/**
 * Recalculate all gap analysis data
 */
export const recalculateGapAnalysis = async (): Promise<{
  message: string;
}> => {
  const response = await apiClient.post("/api/gap-analysis/recalculate");
  return response.data;
};

/**
 * Get all obligation categories
 */
export const getGapCategories = async (): Promise<CategoryCoverage[]> => {
  const response = await apiClient.get<CategoryCoverage[]>(
    "/api/gap-analysis/categories",
  );
  return response.data;
};

/**
 * Get coverage trend over time
 */
export const getCoverageTrend = async (params?: {
  days?: number;
  category?: string;
}): Promise<CoverageTrendPoint[]> => {
  const response = await apiClient.get<CoverageTrendPoint[]>(
    "/api/gap-analysis/trend",
    {
      params,
    },
  );
  return response.data;
};

/**
 * Get all obligation-policy mappings (admin only)
 */
export const getAllMappings = async (params?: {
  skip?: number;
  limit?: number;
}): Promise<{
  mappings: Array<{
    id: string;
    obligation_id: string;
    policy_id: string;
    internal_rule_id: string | null;
    coverage_level: string;
    created_at: string;
  }>;
  total: number;
}> => {
  const response = await apiClient.get("/api/gap-analysis/admin/mappings", {
    params,
  });
  return response.data;
};

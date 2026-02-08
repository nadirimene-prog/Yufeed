// Extended API client with compliance endpoints
import apiClient from "./http";

// ... (keep existing exports from api.ts)

// Compliance API
export interface ComplianceMetrics {
  total_documents: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  upcoming_deadlines_30d: number;
  upcoming_deadlines_60d: number;
  upcoming_deadlines_90d: number;
  by_domain: Record<string, number>;
}

export interface TimelineEvent {
  id: string;
  date: string;
  type:
    | "PROPOSAL"
    | "PUBLICATION"
    | "ENTRY_INTO_FORCE"
    | "AMENDMENT"
    | "CORRIGENDUM"
    | "REPEAL"
    | "CONSOLIDATION";
  title: string;
  description?: string;
  status: "completed" | "pending" | "future";
  related_doc_celex?: string;
}

export interface Annotation {
  id: number;
  content: string;
  article_reference?: string;
  user_email: string;
  created_at: string;
  updated_at: string;
}

export interface AnnotationCreate {
  content: string;
  article_reference?: string;
  user_email: string;
}

export const analyzeDocument = async (
  celex: string,
  force: boolean = false,
) => {
  const response = await apiClient.post(
    `/api/compliance/documents/${celex}/analyze`,
    { force },
  );
  return response.data;
};

export const getAnnotations = async (celex: string): Promise<Annotation[]> => {
  const response = await apiClient.get<Annotation[]>(
    `/api/compliance/documents/${celex}/annotations`,
  );
  return response.data;
};

export const createAnnotation = async (
  celex: string,
  data: AnnotationCreate,
): Promise<Annotation> => {
  const response = await apiClient.post<Annotation>(
    `/api/compliance/documents/${celex}/annotations`,
    data,
  );
  return response.data;
};

export const deleteAnnotation = async (annotationId: number) => {
  const response = await apiClient.delete(
    `/api/compliance/annotations/${annotationId}`,
  );
  return response.data;
};

export const getComplianceMetrics = async (): Promise<ComplianceMetrics> => {
  const response = await apiClient.get<ComplianceMetrics>(
    "/api/compliance/dashboard/metrics",
  );
  return response.data;
};

export const getHighRiskDocuments = async (limit: number = 10) => {
  const response = await apiClient.get(
    `/api/compliance/documents/high-risk?limit=${limit}`,
  );
  return response.data;
};

export const getUpcomingDeadlines = async (days: number = 90) => {
  const response = await apiClient.get(
    `/api/compliance/documents/deadlines?days=${days}`,
  );
  return response.data;
};

export const getDocumentTimeline = async (
  celex: string,
): Promise<TimelineEvent[]> => {
  const response = await apiClient.get<TimelineEvent[]>(
    `/api/compliance/documents/${celex}/timeline`,
  );
  return response.data;
};

// ========== Policy API ==========

import type {
  Policy,
  PolicyCreate,
  PolicyUpdate,
  PolicySection,
  PolicyTemplate,
  RiskCategory,
  RiskCategoryTree,
  RiskEntry,
  RiskEntryCreate,
  RiskEntryUpdate,
  RiskMapSummary,
  RiskHeatMapData,
  ObligationRiskLink,
  Obligation,
  ObligationApprovalData,
} from "@/types/compliance";
import type {
  InternalRule,
  InternalRuleCreatePayload,
  InternalRuleMapping,
  InternalRuleMappingCreatePayload,
} from "@/types/compliance-workflow";

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

// Policy CRUD
export const getPolicies = async (params?: {
  status?: string;
  owner?: string;
  q?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<Policy>> => {
  const response = await apiClient.get<PaginatedResponse<Policy>>(
    "/api/policies",
    { params },
  );
  return response.data;
};

export const createPolicy = async (data: PolicyCreate): Promise<Policy> => {
  const response = await apiClient.post<Policy>("/api/policies", data);
  return response.data;
};

export const getPolicy = async (id: number): Promise<Policy> => {
  const response = await apiClient.get<Policy>(`/api/policies/${id}`);
  return response.data;
};

export const updatePolicy = async (
  id: number,
  data: PolicyUpdate,
): Promise<Policy> => {
  const response = await apiClient.patch<Policy>(`/api/policies/${id}`, data);
  return response.data;
};

export const deletePolicy = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/policies/${id}`);
};

export const approvePolicy = async (
  id: number,
  note?: string,
): Promise<Policy> => {
  const response = await apiClient.post<Policy>(`/api/policies/${id}/approve`, {
    note,
  });
  return response.data;
};

export const getPolicyObligations = async (
  id: number,
  params?: {
    skip?: number;
    limit?: number;
  },
): Promise<PaginatedResponse<Obligation>> => {
  const response = await apiClient.get<PaginatedResponse<Obligation>>(
    `/api/policies/${id}/obligations`,
    { params },
  );
  return response.data;
};

export const getPolicyTemplates = async (params?: {
  category?: string;
  q?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<PolicyTemplate>> => {
  const response = await apiClient.get<PaginatedResponse<PolicyTemplate>>(
    "/api/policies/templates",
    { params },
  );
  return response.data;
};

export const getPolicyTemplateSuggestions = async (
  obligationId: number,
  limit: number = 3,
): Promise<{
  items: Array<{
    policy_document_id: number;
    policy_id: string;
    template_id: string;
    name: string;
    category: string;
    score: number;
  }>;
}> => {
  const response = await apiClient.get(
    `/api/obligations/${obligationId}/policy-suggestions`,
    { params: { limit } },
  );
  return response.data;
};

export const createPolicyFromTemplate = async (
  templateId: string,
  data?: {
    name?: string;
    owner?: string;
    status?: string;
    language?: string;
    effective_date?: string;
    source_url?: string;
    content?: string;
    metadata?: Record<string, unknown>;
  },
): Promise<Policy> => {
  const response = await apiClient.post<Policy>(
    `/api/policies/from-template/${templateId}`,
    data ?? {},
  );
  return response.data;
};

export const linkObligationToPolicy = async (
  policyId: number,
  obligationId: number,
): Promise<{ message: string; policy_id: string; obligation_id: string }> => {
  const response = await apiClient.post(
    `/api/policies/${policyId}/link-obligation/${obligationId}`,
  );
  return response.data;
};

// Policy Sections
export const getPolicySections = async (
  policyId: number,
): Promise<{ items: PolicySection[] }> => {
  const response = await apiClient.get<{ items: PolicySection[] }>(
    `/api/policies/${policyId}/sections`,
  );
  return response.data;
};

export const createPolicySection = async (
  policyId: number,
  data: Partial<PolicySection>,
): Promise<PolicySection> => {
  const response = await apiClient.post<PolicySection>(
    `/api/policies/${policyId}/sections`,
    data,
  );
  return response.data;
};

export const updatePolicySection = async (
  sectionId: number,
  data: Partial<PolicySection>,
): Promise<PolicySection> => {
  const response = await apiClient.patch<PolicySection>(
    `/api/policies/sections/${sectionId}`,
    data,
  );
  return response.data;
};

export const deletePolicySection = async (sectionId: number): Promise<void> => {
  await apiClient.delete(`/api/policies/sections/${sectionId}`);
};

// ========== Risk API ==========

// Risk Categories
export const getRiskCategories = async (params?: {
  status?: string;
  parent_id?: number;
}): Promise<{ items: RiskCategory[] }> => {
  const response = await apiClient.get<{ items: RiskCategory[] }>(
    "/api/risk/categories",
    { params },
  );
  return response.data;
};

export const getRiskCategoryTree = async (): Promise<{
  items: RiskCategoryTree[];
}> => {
  const response = await apiClient.get<{ items: RiskCategoryTree[] }>(
    "/api/risk/categories/tree",
  );
  return response.data;
};

export const createRiskCategory = async (
  data: Partial<RiskCategory>,
): Promise<RiskCategory> => {
  const response = await apiClient.post<RiskCategory>(
    "/api/risk/categories",
    data,
  );
  return response.data;
};

export const getRiskCategory = async (id: number): Promise<RiskCategory> => {
  const response = await apiClient.get<RiskCategory>(
    `/api/risk/categories/${id}`,
  );
  return response.data;
};

export const updateRiskCategory = async (
  id: number,
  data: Partial<RiskCategory>,
): Promise<RiskCategory> => {
  const response = await apiClient.patch<RiskCategory>(
    `/api/risk/categories/${id}`,
    data,
  );
  return response.data;
};

export const deleteRiskCategory = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/risk/categories/${id}`);
};

// Risk Entries
export const getRiskEntries = async (params?: {
  category_id?: number;
  inherent_risk_level?: string;
  residual_risk_level?: string;
  mitigation_status?: string;
  q?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedResponse<RiskEntry>> => {
  const response = await apiClient.get<PaginatedResponse<RiskEntry>>(
    "/api/risk/entries",
    { params },
  );
  return response.data;
};

export const createRiskEntry = async (
  data: RiskEntryCreate,
): Promise<RiskEntry> => {
  const response = await apiClient.post<RiskEntry>("/api/risk/entries", data);
  return response.data;
};

export const getRiskEntry = async (id: number): Promise<RiskEntry> => {
  const response = await apiClient.get<RiskEntry>(`/api/risk/entries/${id}`);
  return response.data;
};

export const updateRiskEntry = async (
  id: number,
  data: RiskEntryUpdate,
): Promise<RiskEntry> => {
  const response = await apiClient.patch<RiskEntry>(
    `/api/risk/entries/${id}`,
    data,
  );
  return response.data;
};

export const deleteRiskEntry = async (id: number): Promise<void> => {
  await apiClient.delete(`/api/risk/entries/${id}`);
};

// Obligation-Risk Links
export const getRiskEntryObligations = async (
  entryId: number,
): Promise<{ items: ObligationRiskLink[] }> => {
  const response = await apiClient.get<{ items: ObligationRiskLink[] }>(
    `/api/risk/entries/${entryId}/obligations`,
  );
  return response.data;
};

export const linkObligationToRisk = async (
  entryId: number,
  data: { obligation_id: number; link_type?: string; notes?: string },
): Promise<ObligationRiskLink> => {
  const response = await apiClient.post<ObligationRiskLink>(
    `/api/risk/entries/${entryId}/obligations`,
    data,
  );
  return response.data;
};

export const deleteObligationRiskLink = async (
  linkId: number,
): Promise<void> => {
  await apiClient.delete(`/api/risk/links/${linkId}`);
};

// Risk Map Overview
export const getRiskMap = async (): Promise<RiskMapSummary> => {
  const response = await apiClient.get<RiskMapSummary>("/api/risk/map");
  return response.data;
};

export const getRiskHeatmap = async (): Promise<RiskHeatMapData> => {
  const response = await apiClient.get<RiskHeatMapData>("/api/risk/heatmap");
  return response.data;
};

// ========== Enhanced Obligations API ==========

export interface ObligationsListResponse extends PaginatedResponse<Obligation> {
  status_counts?: Record<string, number>;
}

export const getObligations = async (params?: {
  status?: string;
  jurisdiction?: string;
  source_system?: string;
  scope?: string;
  q?: string;
  include_status_counts?: boolean;
  skip?: number;
  limit?: number;
}): Promise<ObligationsListResponse> => {
  const response = await apiClient.get<ObligationsListResponse>(
    "/api/obligations",
    { params },
  );
  return response.data;
};

export const getObligation = async (id: number): Promise<Obligation> => {
  const response = await apiClient.get<Obligation>(`/api/obligations/${id}`);
  return response.data;
};

export const updateObligationStatus = async (
  id: number,
  data: { status: string; note?: string },
): Promise<Obligation> => {
  const response = await apiClient.patch<Obligation>(
    `/api/obligations/${id}`,
    data,
  );
  return response.data;
};

export const approveObligation = async (
  id: number,
  data: ObligationApprovalData,
): Promise<Obligation> => {
  const response = await apiClient.patch<Obligation>(
    `/api/obligations/${id}/approve`,
    data,
  );
  return response.data;
};

export const getObligationRisks = async (
  id: number,
): Promise<{ items: ObligationRiskLink[] }> => {
  const response = await apiClient.get<{ items: ObligationRiskLink[] }>(
    `/api/obligations/${id}/risks`,
  );
  return response.data;
};

export const getObligationInternalRules = async (
  id: number,
): Promise<{ items: InternalRule[] }> => {
  const response = await apiClient.get<{ items: InternalRule[] }>(
    `/api/compliance/obligations/${id}/internal-rules`,
  );
  return response.data;
};

export const createComplianceInternalRule = async (
  obligationId: number,
  payload: InternalRuleCreatePayload,
): Promise<InternalRule> => {
  const response = await apiClient.post<InternalRule>(
    `/api/compliance/obligations/${obligationId}/internal-rules`,
    payload,
  );
  return response.data;
};

export const createComplianceInternalRuleMapping = async (
  internalRuleId: number,
  payload: InternalRuleMappingCreatePayload,
): Promise<InternalRuleMapping> => {
  const response = await apiClient.post<InternalRuleMapping>(
    `/api/compliance/internal-rules/${internalRuleId}/mappings`,
    payload,
  );
  return response.data;
};

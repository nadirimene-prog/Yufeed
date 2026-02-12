import apiClient from "@/lib/http";
import type {
  Finding,
  FindingListParams,
  CaseDecision,
  DecisionListParams,
  EvidencePack,
  EvidencePackDetail,
  EvidencePackListParams,
} from "@/types/workbench";

// ─── Findings ───────────────────────────────────────────────────
export async function getFindings(
  params?: FindingListParams,
): Promise<Finding[]> {
  const cleanParams: Record<string, unknown> = { limit: params?.limit ?? 50 };
  if (params?.status && params.status.length > 0)
    cleanParams.status = params.status;
  if (params?.severity && params.severity.length > 0)
    cleanParams.severity = params.severity;
  if (params?.finding_type && params.finding_type.length > 0)
    cleanParams.finding_type = params.finding_type;
  if (params?.assigned_to && params.assigned_to.length > 0)
    cleanParams.assigned_to = params.assigned_to;
  const response = await apiClient.get<Finding[]>("/api/findings/", {
    params: cleanParams,
  });
  return response.data;
}

export async function getFinding(id: number): Promise<Finding> {
  const response = await apiClient.get<Finding>(`/api/findings/${id}`);
  return response.data;
}

export async function closeFinding(
  id: number,
  data: { reason: string; comment: string },
): Promise<Finding> {
  const response = await apiClient.post<Finding>(
    `/api/findings/${id}/close`,
    data,
  );
  return response.data;
}

export async function escalateFinding(
  id: number,
  data: { case_id: string },
): Promise<Finding> {
  const response = await apiClient.post<Finding>(
    `/api/findings/${id}/escalate`,
    data,
  );
  return response.data;
}

export async function acknowledgeFinding(id: number): Promise<Finding> {
  const response = await apiClient.post<Finding>(
    `/api/findings/${id}/acknowledge`,
  );
  return response.data;
}

// ─── Case Decisions ─────────────────────────────────────────────
export async function getCaseDecisions(
  caseId: string,
  params?: DecisionListParams,
): Promise<CaseDecision[]> {
  const cleanParams: Record<string, unknown> = { limit: params?.limit ?? 50 };
  if (params?.status && params.status.length > 0)
    cleanParams.status = params.status;
  const response = await apiClient.get<CaseDecision[]>(
    `/api/cases/${caseId}/decisions/`,
    { params: cleanParams },
  );
  return response.data;
}

export async function createCaseDecision(
  caseId: string,
  data: { disposition: string; rationale: string },
): Promise<CaseDecision> {
  const response = await apiClient.post<CaseDecision>(
    `/api/cases/${caseId}/decisions/`,
    data,
  );
  return response.data;
}

export async function submitCaseDecision(
  caseId: string,
  decisionId: number,
): Promise<CaseDecision> {
  const response = await apiClient.post<CaseDecision>(
    `/api/cases/${caseId}/decisions/${decisionId}/submit`,
  );
  return response.data;
}

export async function approveCaseDecision(
  caseId: string,
  decisionId: number,
): Promise<CaseDecision> {
  const response = await apiClient.post<CaseDecision>(
    `/api/cases/${caseId}/decisions/${decisionId}/approve`,
  );
  return response.data;
}

export async function rejectCaseDecision(
  caseId: string,
  decisionId: number,
  data: { reason: string },
): Promise<CaseDecision> {
  const response = await apiClient.post<CaseDecision>(
    `/api/cases/${caseId}/decisions/${decisionId}/reject`,
    data,
  );
  return response.data;
}

// ─── Evidence Packs ─────────────────────────────────────────────
export async function getEvidencePacks(
  caseId: string,
  params?: EvidencePackListParams,
): Promise<EvidencePack[]> {
  const cleanParams: Record<string, unknown> = { limit: params?.limit ?? 50 };
  const response = await apiClient.get<EvidencePack[]>(
    `/api/cases/${caseId}/evidence-packs/`,
    { params: cleanParams },
  );
  return response.data;
}

export async function getEvidencePackDetail(
  caseId: string,
  packId: string,
): Promise<EvidencePackDetail> {
  const response = await apiClient.get<EvidencePackDetail>(
    `/api/cases/${caseId}/evidence-packs/${packId}`,
  );
  return response.data;
}

export async function createEvidencePack(
  caseId: string,
): Promise<EvidencePack> {
  const response = await apiClient.post<EvidencePack>(
    `/api/cases/${caseId}/evidence-packs/`,
  );
  return response.data;
}

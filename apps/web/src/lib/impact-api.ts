/**
 * API client for Impact Assessment features
 */
import apiClient from "./http";

export interface ImpactAssessment {
  id: number;
  doc_id: number;
  overall_impact_level: string;
  executive_summary: string | null;
  affected_areas_json: { areas: string[] } | null;
  key_changes: { changes: string[] } | null;
  estimated_effort_hours: number | null;
  estimated_cost: number | null;
  requires_system_changes: boolean;
  requires_process_changes: boolean;
  requires_policy_updates: boolean;
  assessed_at: string;
  action_items: ActionItem[];
}

export interface ActionItem {
  id: number;
  title: string;
  description: string | null;
  business_area: string;
  priority: number;
  estimated_hours: number | null;
  complexity: string | null;
  assigned_to: string | null;
  status: string;
  target_date: string | null;
  progress_percentage: number;
  created_at: string;
  updated_at: string;
}

export interface ActionItemWithDoc extends ActionItem {
  document: {
    celex: string;
    title: string;
  } | null;
}

export interface ImpactStats {
  total_assessments: number;
  critical_high_impact: number;
  total_action_items: number;
  completed_actions: number;
  blocked_actions: number;
  completion_rate: number;
  actions_by_business_area: Record<string, number>;
  total_estimated_effort_hours: number;
  total_estimated_cost_eur: number;
}

export async function analyzeDocumentImpact(
  celex: string,
  force: boolean = false,
) {
  const response = await apiClient.post(
    `/api/impact/documents/${celex}/analyze`,
    { force },
  );
  return response.data;
}

export async function getImpactAssessment(
  celex: string,
): Promise<ImpactAssessment> {
  const response = await apiClient.get(
    `/api/impact/documents/${celex}/assessment`,
  );
  return response.data;
}

export async function getActionItems(celex: string): Promise<ActionItem[]> {
  const response = await apiClient.get(
    `/api/impact/documents/${celex}/actions`,
  );
  return response.data;
}

export async function updateActionItem(
  actionId: number,
  update: {
    status?: string;
    assigned_to?: string;
    progress_percentage?: number;
    notes?: string;
    target_date?: string;
  },
) {
  const response = await apiClient.put(
    `/api/impact/actions/${actionId}`,
    update,
  );
  return response.data;
}

export async function getAllActionItems(filters?: {
  status?: string;
  business_area?: string;
  assigned_to?: string;
}): Promise<ActionItemWithDoc[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.append("status", filters.status);
  if (filters?.business_area)
    params.append("business_area", filters.business_area);
  if (filters?.assigned_to) params.append("assigned_to", filters.assigned_to);

  const response = await apiClient.get(
    `/api/impact/actions/all?${params.toString()}`,
  );
  return response.data;
}

export async function getImpactDashboardStats(): Promise<ImpactStats> {
  const response = await apiClient.get(`/api/impact/dashboard/stats`);
  return response.data;
}

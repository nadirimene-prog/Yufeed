/**
 * Policy Generator API Client
 *
 * API endpoints for AI-powered policy generation from obligations.
 */
import apiClient from "./http";

// Types
export interface PolicyTemplate {
  template_id: string;
  name: string;
  category: string;
  description: string;
  variable_count: number;
}

export interface TemplateVariable {
  name: string;
  description: string;
  required: boolean;
  default_value?: string;
}

export interface TemplateDetail extends PolicyTemplate {
  variables: TemplateVariable[];
  sections: string[];
}

export interface GeneratePolicyRequest {
  template_id: string;
  obligation_ids: string[];
  custom_variables?: Record<string, string>;
  options?: {
    include_procedures?: boolean;
    include_controls?: boolean;
    include_templates?: boolean;
    tone?: "formal" | "balanced" | "simple";
  };
}

export interface QuickGenerateRequest {
  name: string;
  description?: string;
  category?: string;
  obligations?: string[];
}

export interface GenerationJob {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  template_id: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface PolicyGenerationResult {
  job_id: string;
  status: "completed";
  generated_content: string;
  word_count: number;
  sections: Array<{
    title: string;
    content: string;
  }>;
  obligations_addressed: string[];
  ai_confidence: number;
  generated_at: string;
}

export interface GenerationStats {
  total_generations: number;
  approved: number;
  rejected: number;
  pending: number;
  average_word_count: number;
  top_templates: Array<{
    template_id: string;
    name: string;
    usage_count: number;
  }>;
}

// API Functions

/**
 * Get all policy templates
 */
export const getPolicyTemplates = async (params?: {
  category?: string;
  skip?: number;
  limit?: number;
}): Promise<{ templates: PolicyTemplate[]; total: number }> => {
  const response = await apiClient.get("/api/policy-generator/templates", {
    params,
  });
  return response.data;
};

/**
 * Get template variables
 */
export const getTemplateVariables = async (
  templateId: string,
): Promise<TemplateVariable[]> => {
  const response = await apiClient.get<TemplateVariable[]>(
    `/api/policy-generator/templates/${templateId}/variables`,
  );
  return response.data;
};

/**
 * Preview a template with variables
 */
export const previewTemplate = async (
  templateId: string,
  variables: Record<string, string>,
): Promise<{ preview: string }> => {
  const response = await apiClient.post(
    `/api/policy-generator/templates/${templateId}/preview`,
    { variables },
  );
  return response.data;
};

/**
 * Generate a policy from obligations
 */
export const generatePolicy = async (
  data: GeneratePolicyRequest,
): Promise<{ status: string; job_id: string }> => {
  const response = await apiClient.post("/api/policy-generator/generate", data);
  return response.data;
};

/**
 * Quick generate a policy (simplified flow)
 */
export const quickGeneratePolicy = async (
  data: QuickGenerateRequest,
): Promise<{ status: string; job_id: string }> => {
  const response = await apiClient.post(
    "/api/policy-generator/quick-generate",
    data,
  );
  return response.data;
};

/**
 * Get all generation jobs
 */
export const getGenerationJobs = async (params?: {
  status?: "queued" | "processing" | "completed" | "failed";
  skip?: number;
  limit?: number;
}): Promise<{ jobs: GenerationJob[]; total: number }> => {
  const response = await apiClient.get("/api/policy-generator/jobs", {
    params,
  });
  return response.data;
};

/**
 * Get generation result
 */
export const getGenerationResult = async (
  jobId: string,
): Promise<PolicyGenerationResult> => {
  const response = await apiClient.get<PolicyGenerationResult>(
    `/api/policy-generator/results/${jobId}`,
  );
  return response.data;
};

/**
 * Preview generated policy
 */
export const previewGeneratedPolicy = async (
  jobId: string,
): Promise<{
  content: string;
  sections: Array<{ title: string; content: string }>;
}> => {
  const response = await apiClient.get(
    `/api/policy-generator/results/${jobId}/preview`,
  );
  return response.data;
};

/**
 * Approve generated policy
 */
export const approveGeneratedPolicy = async (
  jobId: string,
  data?: { title?: string; owner?: string },
): Promise<{ message: string; policy_id: string }> => {
  const response = await apiClient.post(
    `/api/policy-generator/results/${jobId}/approve`,
    data || {},
  );
  return response.data;
};

/**
 * Reject generated policy
 */
export const rejectGeneratedPolicy = async (
  jobId: string,
  reason?: string,
): Promise<{ message: string }> => {
  const response = await apiClient.post(
    `/api/policy-generator/results/${jobId}/reject`,
    { reason },
  );
  return response.data;
};

/**
 * Get generation statistics
 */
export const getGenerationStats = async (): Promise<GenerationStats> => {
  const response = await apiClient.get<GenerationStats>(
    "/api/policy-generator/stats",
  );
  return response.data;
};

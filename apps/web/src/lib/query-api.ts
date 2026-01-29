/**
 * API client for Natural Language Query features
 */
import apiClient from "./http";

export interface SourceDocument {
    celex: string;
    title: string;
    relevance_score: number;
    publication_date: string | null;
    compliance_domain: string | null;
    risk_level: string | null;
}

export interface QueryResponse {
    query: string;
    answer: string;
    confidence: string;
    sources: SourceDocument[];
    document_count: number;
    model: string | null;
    followup_questions: string[] | null;
}

export interface QueryRequest {
    query: string;
    compliance_domain?: string;
    risk_level?: string;
    max_documents?: number;
}

export interface ConversationRequest {
    query: string;
    conversation_id?: string;
    filters?: Record<string, any>;
}

export interface QuerySuggestions {
    domain: string;
    suggestions: string[] | Record<string, string[]>;
}

export async function askQuestion(request: QueryRequest): Promise<QueryResponse> {
    const response = await apiClient.post(`/api/query/ask`, request);
    return response.data;
}

export async function conversationTurn(request: ConversationRequest): Promise<QueryResponse> {
    const response = await apiClient.post(`/api/query/conversation`, request);
    return response.data;
}

export async function clearConversation(conversationId: string): Promise<void> {
    await apiClient.delete(`/api/query/conversation/${conversationId}`);
}

export async function getQuerySuggestions(domain?: string): Promise<QuerySuggestions> {
    const params = domain ? `?domain=${domain}` : '';
    const response = await apiClient.get(`/api/query/suggestions${params}`);
    return response.data;
}

export async function queryHealthCheck(): Promise<{ status: string; ai_available: boolean; active_conversations: number }> {
    const response = await apiClient.get(`/api/query/health`);
    return response.data;
}

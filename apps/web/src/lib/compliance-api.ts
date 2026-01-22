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
    type: 'PROPOSAL' | 'PUBLICATION' | 'ENTRY_INTO_FORCE' | 'AMENDMENT' | 'CORRIGENDUM' | 'REPEAL' | 'CONSOLIDATION';
    title: string;
    description?: string;
    status: 'completed' | 'pending' | 'future';
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

export const analyzeDocument = async (celex: string, force: boolean = false) => {
    const response = await apiClient.post(`/compliance/documents/${celex}/analyze`, { force });
    return response.data;
};

export const getAnnotations = async (celex: string): Promise<Annotation[]> => {
    const response = await apiClient.get<Annotation[]>(`/compliance/documents/${celex}/annotations`);
    return response.data;
};

export const createAnnotation = async (celex: string, data: AnnotationCreate): Promise<Annotation> => {
    const response = await apiClient.post<Annotation>(`/compliance/documents/${celex}/annotations`, data);
    return response.data;
};

export const deleteAnnotation = async (annotationId: number) => {
    const response = await apiClient.delete(`/compliance/annotations/${annotationId}`);
    return response.data;
};

export const getComplianceMetrics = async (): Promise<ComplianceMetrics> => {
    const response = await apiClient.get<ComplianceMetrics>('/compliance/dashboard/metrics');
    return response.data;
};

export const getHighRiskDocuments = async (limit: number = 10) => {
    const response = await apiClient.get(`/compliance/documents/high-risk?limit=${limit}`);
    return response.data;
};

export const getUpcomingDeadlines = async (days: number = 90) => {
    const response = await apiClient.get(`/compliance/documents/deadlines?days=${days}`);
    return response.data;
};

export const getDocumentTimeline = async (celex: string): Promise<TimelineEvent[]> => {
    // Mock data simulation based on CELEX
    // In a real app, this would fetch from /compliance/documents/{celex}/timeline

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));

    const baseYear = parseInt(celex.substring(1, 5)) || 2024;

    return [
        {
            id: '1',
            date: `${baseYear - 1}-05-20`,
            type: 'PROPOSAL',
            title: 'Commission Proposal',
            description: 'Initial proposal by the European Commission',
            status: 'completed'
        },
        {
            id: '2',
            date: `${baseYear}-06-15`,
            type: 'PUBLICATION',
            title: 'Published in Official Journal',
            description: 'Official publication in the OJEU',
            status: 'completed'
        },
        {
            id: '3',
            date: `${baseYear}-06-25`,
            type: 'ENTRY_INTO_FORCE',
            title: 'Entry into Force',
            description: 'The act enters into force 20 days after publication',
            status: 'completed'
        },
        {
            id: '4',
            date: `${baseYear + 1}-01-01`,
            type: 'AMENDMENT',
            title: 'Amendment by Reg 2025/123',
            description: 'Minor technical amendments to Article 4',
            status: 'completed',
            related_doc_celex: '32025R0123'
        },
        {
            id: '5',
            date: `${baseYear + 2}-02-14`,
            type: 'CONSOLIDATION',
            title: 'Consolidated Version Available',
            description: 'Unofficial consolidated text produced by the Publications Office',
            status: 'completed'
        },
        {
            id: '6',
            date: `${baseYear + 3}-12-31`,
            type: 'REPEAL',
            title: 'Expected Repeal',
            description: 'Scheduled review and potential repeal by new framework',
            status: 'future'
        }
    ];
};

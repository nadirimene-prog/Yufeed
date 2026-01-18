import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Search API
export interface SearchParams {
  q?: string;
  type?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  limit?: number;
}

export interface SearchResultItem {
  celex: string;
  title: string;
  publication_date?: string;
  status?: string;
  score?: number;
}

export interface SearchResponse {
  total: number;
  results: SearchResultItem[];
}

export const searchDocuments = async (params: SearchParams): Promise<SearchResponse> => {
  const response = await apiClient.get<SearchResponse>('/search', { params });
  return response.data;
};

// Documents API
export interface LegalDocument {
  id: number;
  celex: string;
  title: string;
  type?: string;
  publication_date?: string;
  entry_into_force_date?: string;
  status: string;
  last_modified: string;
  eli?: string;
  cellar_id?: string;
}

export const getDocument = async (celex: string): Promise<LegalDocument> => {
  const response = await apiClient.get<LegalDocument>(`/documents/${celex}`);
  return response.data;
};

// Watchlists API
export interface WatchlistCreate {
  name: string;
  mode?: string;
  rss_url?: string;
  query_json: Record<string, any>;
  curated_celex_json?: Record<string, any>;
  recipients_json?: Record<string, any>;
  schedule?: string;
}

export interface Watchlist extends WatchlistCreate {
  id: number;
}

export const createWatchlist = async (data: WatchlistCreate): Promise<Watchlist> => {
  const response = await apiClient.post<Watchlist>('/watchlists', data);
  return response.data;
};

export const getWatchlists = async (): Promise<Watchlist[]> => {
  const response = await apiClient.get<Watchlist[]>('/watchlists');
  return response.data;
};

// Alerts API
export interface AlertEvent {
  id: number;
  event_type: string;
  detected_at: string;
  doc_id: number;
  watchlist_id?: number;
}

export const getAlerts = async (): Promise<AlertEvent[]> => {
  const response = await apiClient.get<AlertEvent[]>('/alerts');
  return response.data;
};

export const getWatchlistAlerts = async (watchlistId: number): Promise<AlertEvent[]> => {
  const response = await apiClient.get<AlertEvent[]>(`/watchlists/${watchlistId}/alerts`);
  return response.data;
};

export default apiClient;

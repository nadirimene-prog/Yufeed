import apiClient from "./http";

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

export const searchDocuments = async (
  params: SearchParams,
): Promise<SearchResponse> => {
  const response = await apiClient.get<SearchResponse>("/api/search", {
    params,
  });
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
  const response = await apiClient.get<LegalDocument>(
    `/api/documents/${celex}`,
  );
  return response.data;
};

// Watchlists API
export interface WatchlistQuery {
  search_term?: string;
  doc_types?: string[];
  domains?: string[];
  date_range?: { from?: string; to?: string };
  [key: string]: unknown;
}

export interface WatchlistRecipient {
  email: string;
  name?: string;
}

export interface WatchlistCreate {
  name: string;
  mode?: string;
  rss_url?: string;
  query_json: WatchlistQuery;
  curated_celex_json?: { celex_ids: string[] };
  recipients_json?: { recipients: WatchlistRecipient[] };
  schedule?: string;
}

export interface Watchlist extends WatchlistCreate {
  id: number;
}

export const createWatchlist = async (
  data: WatchlistCreate,
): Promise<Watchlist> => {
  const response = await apiClient.post<Watchlist>("/api/watchlists", data);
  return response.data;
};

export const getWatchlists = async (
  params?: Record<string, unknown>,
): Promise<Watchlist[]> => {
  const response = await apiClient.get<Watchlist[]>("/api/watchlists", {
    params,
  });
  return response.data;
};

export const addWatchlistEntry = async (
  watchlistId: string,
  entry: Record<string, unknown>,
): Promise<unknown> => {
  const response = await apiClient.post(
    `/api/watchlists/${watchlistId}/entries`,
    entry,
  );
  return response.data;
};

export const removeWatchlistEntry = async (
  watchlistId: string,
  entryId: string,
): Promise<void> => {
  await apiClient.delete(`/api/watchlists/${watchlistId}/entries/${entryId}`);
};

// Alerts API
export interface AlertEvent {
  id: number;
  event_type: string;
  detected_at: string;
  doc_id: number;
  watchlist_id?: number;
  document?: {
    celex: string;
    title: string;
  };
}

export const getAlerts = async (
  params?: Record<string, unknown>,
): Promise<AlertEvent[]> => {
  const response = await apiClient.get<AlertEvent[]>("/api/alerts", { params });
  return response.data;
};

export const getAlert = async (id: string): Promise<AlertEvent> => {
  const response = await apiClient.get<AlertEvent>(`/api/alerts/${id}`);
  return response.data;
};

export const updateAlert = async (
  id: string,
  data: Record<string, unknown>,
): Promise<AlertEvent> => {
  const response = await apiClient.patch<AlertEvent>(`/api/alerts/${id}`, data);
  return response.data;
};

export const getWatchlistAlerts = async (
  watchlistId: number,
): Promise<AlertEvent[]> => {
  const response = await apiClient.get<AlertEvent[]>(
    `/api/watchlists/${watchlistId}/alerts`,
  );
  return response.data;
};

export default apiClient;

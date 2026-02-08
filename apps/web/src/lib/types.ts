export interface LegalDocument {
  celex: string;
  title: string;
  type: "Directive" | "Regulation" | "Decision" | "Other";
  status: "In Force" | "No Longer in Force" | "Proposal" | "Unknown";
  date: string; // ISO date string
  topics: string[];
}

export type SearchFilters = {
  query: string;
  type?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
  topic?: string;
};

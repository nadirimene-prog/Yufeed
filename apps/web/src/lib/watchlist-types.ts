export interface Watchlist {
  id: string;
  name: string;
  type: "rss" | "celex";
  source: string; // URL or Comma-separated CELEX
  recipients: string[];
  schedule: "daily" | "weekly";
  lastRun?: string;
}

export interface WatchlistEntry {
  id?: string;
  celex?: string;
  title?: string;
  url?: string;
  added_at?: string;
  [key: string]: unknown;
}

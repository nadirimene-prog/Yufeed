"use client";

import { useState, useEffect } from "react";
import SearchBar from "@/components/search-bar";
import Filters from "@/components/filters";
import ResultsTable from "@/components/results-table";
import type { LegalDocument, SearchFilters } from "@/lib/types";
import { searchDocuments, type SearchResultItem } from "@/lib/api";
import { logger } from "@/lib/logger";
import { ExportButton } from "@/components/ui/export-button";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({ query: "" });
  const [results, setResults] = useState<LegalDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Convert backend SearchResultItem to frontend LegalDocument
  const mapToLegalDocument = (item: SearchResultItem): LegalDocument => ({
    celex: item.celex,
    title: item.title,
    type: "Regulation", // Default, could be enhanced with backend data
    status: item.status === "active" ? "In Force" : "No Longer in Force",
    date: item.publication_date ?? new Date().toISOString(),
    topics: [], // Could be extracted from metadata if available
  });

  const handleSearch = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await searchDocuments({
        q: query || undefined,
        type: filters.type,
        status: filters.status === "In Force" ? "active" : filters.status,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        page: 1,
        limit: 20,
      });

      const mappedResults = response.results.map(mapToLegalDocument);
      setResults(mappedResults);
      setTotal(response.total);
    } catch (err) {
      logger.error("Search failed:", err);
      setError(
        "Failed to search documents. Please check if the backend is running.",
      );
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Search on mount and when filters change
  useEffect(() => {
    handleSearch();
  }, [filters.status, filters.type]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex items-start justify-between">
        <div className="text-center md:text-left space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900  sm:text-4xl">
            Search Legal Documents
          </h1>
          <p className="text-lg text-slate-600  max-w-2xl">
            Access the latest EU regulations, directives, and decisions with
            real-time updates.
          </p>
          {total > 0 && (
            <p className="text-sm text-slate-500">
              Found {total} document{total !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        {results.length > 0 && (
          <ExportButton
            data={results as unknown as Record<string, unknown>[]}
            filename="legal-documents"
            pdfTitle="Legal Documents Search Results"
            loading={isLoading}
          />
        )}
      </div>

      <SearchBar
        value={query}
        onChange={setQuery}
        onSearch={handleSearch}
        className="mb-8"
      />

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-red-800  ">{error}</div>
      )}

      <div className="grid gap-8 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <div className="sticky top-24 rounded-xl border border-slate-200 bg-white p-6 shadow-sm   backdrop-blur-sm">
            <Filters filters={filters} onChange={setFilters} />
          </div>
        </div>

        <div className="lg:col-span-3">
          <ResultsTable results={results} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}

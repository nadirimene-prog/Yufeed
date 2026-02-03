"use client";

/**
 * Sanctions Screening Page
 *
 * Screen individuals and entities against global sanctions lists.
 * Supports EU Consolidated List and OFAC SDN.
 */

import { useState } from "react";
import Link from "next/link";
import {
  Shield,
  Search,
  ArrowLeft,
  AlertTriangle,
  CheckCircle,
  Loader2,
  User,
  Building,
  Globe,
  Download,
  Plus,
  Trash2,
} from "lucide-react";
import amlOfficerApi, { SanctionsScreenResult, SanctionsMatch } from "@/lib/aml-officer-api";

interface ScreeningEntry {
  id: string;
  name: string;
  entityType: "individual" | "entity";
  nationality?: string;
  birthDate?: string;
}

export default function SanctionsScreeningPage() {
  const [entries, setEntries] = useState<ScreeningEntry[]>([
    { id: "1", name: "", entityType: "individual" },
  ]);
  const [results, setResults] = useState<SanctionsScreenResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLists, setSelectedLists] = useState<string[]>([
    "eu_consolidated",
    "ofac_sdn",
  ]);

  const addEntry = () => {
    setEntries([
      ...entries,
      {
        id: Date.now().toString(),
        name: "",
        entityType: "individual",
      },
    ]);
  };

  const removeEntry = (id: string) => {
    if (entries.length > 1) {
      setEntries(entries.filter((e) => e.id !== id));
    }
  };

  const updateEntry = (id: string, updates: Partial<ScreeningEntry>) => {
    setEntries(
      entries.map((e) => (e.id === id ? { ...e, ...updates } : e))
    );
  };

  const handleScreen = async () => {
    const validEntries = entries.filter((e) => e.name.trim());
    if (validEntries.length === 0) return;

    setLoading(true);
    setResults([]);

    try {
      if (validEntries.length === 1) {
        // Single screening
        const entry = validEntries[0];
        const result = await amlOfficerApi.screenSanctions({
          name: entry.name,
          entity_type: entry.entityType,
          nationality: entry.nationality,
          birth_date: entry.birthDate,
          lists: selectedLists,
        });
        setResults([result]);
      } else {
        // Batch screening
        const result = await amlOfficerApi.batchScreenSanctions({
          names: validEntries.map((e) => e.name),
          max_concurrent: 10,
        });
        setResults(result.results);
      }
    } catch (error) {
      console.error("Screening failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const getMatchSeverity = (score: number) => {
    if (score >= 95) return { color: "text-red-600 bg-red-50", label: "Exact Match" };
    if (score >= 85) return { color: "text-orange-600 bg-orange-50", label: "Strong Match" };
    if (score >= 70) return { color: "text-yellow-600 bg-yellow-50", label: "Partial Match" };
    return { color: "text-gray-600 bg-gray-50", label: "Weak Match" };
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/aml-officer"
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Shield className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  Sanctions Screening
                </h1>
                <p className="text-sm text-gray-500">
                  Screen against EU & OFAC sanctions lists
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input Panel */}
          <div className="space-y-6">
            {/* List Selection */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-medium text-gray-700 mb-4">
                Sanctions Lists
              </h2>
              <div className="flex flex-wrap gap-3">
                {[
                  { id: "eu_consolidated", label: "EU Consolidated List", icon: Globe },
                  { id: "ofac_sdn", label: "OFAC SDN", icon: Shield },
                ].map((list) => (
                  <button
                    key={list.id}
                    onClick={() => {
                      if (selectedLists.includes(list.id)) {
                        if (selectedLists.length > 1) {
                          setSelectedLists(selectedLists.filter((l) => l !== list.id));
                        }
                      } else {
                        setSelectedLists([...selectedLists, list.id]);
                      }
                    }}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition ${
                      selectedLists.includes(list.id)
                        ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                        : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <list.icon className="w-4 h-4" />
                    <span className="text-sm">{list.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Screening Entries */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-medium text-gray-700">
                  Names to Screen
                </h2>
                <button
                  onClick={addEntry}
                  className="flex items-center space-x-1 text-sm text-indigo-600 hover:text-indigo-700"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Entry</span>
                </button>
              </div>

              <div className="space-y-4">
                {entries.map((entry, index) => (
                  <div
                    key={entry.id}
                    className="p-4 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500">
                        Entry {index + 1}
                      </span>
                      {entries.length > 1 && (
                        <button
                          onClick={() => removeEntry(entry.id)}
                          className="text-gray-400 hover:text-red-500 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>

                    {/* Name Input */}
                    <input
                      type="text"
                      value={entry.name}
                      onChange={(e) =>
                        updateEntry(entry.id, { name: e.target.value })
                      }
                      placeholder="Enter name to screen..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent mb-3"
                    />

                    <div className="grid grid-cols-3 gap-3">
                      {/* Entity Type */}
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Type
                        </label>
                        <select
                          value={entry.entityType}
                          onChange={(e) =>
                            updateEntry(entry.id, {
                              entityType: e.target.value as "individual" | "entity",
                            })
                          }
                          className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                          <option value="individual">Individual</option>
                          <option value="entity">Entity</option>
                        </select>
                      </div>

                      {/* Nationality */}
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">
                          Nationality
                        </label>
                        <input
                          type="text"
                          value={entry.nationality || ""}
                          onChange={(e) =>
                            updateEntry(entry.id, { nationality: e.target.value })
                          }
                          placeholder="Optional"
                          className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>

                      {/* Birth Date (for individuals) */}
                      {entry.entityType === "individual" && (
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">
                            DOB
                          </label>
                          <input
                            type="date"
                            value={entry.birthDate || ""}
                            onChange={(e) =>
                              updateEntry(entry.id, { birthDate: e.target.value })
                            }
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={handleScreen}
                disabled={loading || !entries.some((e) => e.name.trim())}
                className="w-full mt-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Screening...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-5 h-5" />
                    <span>
                      Screen {entries.filter((e) => e.name.trim()).length} Name
                      {entries.filter((e) => e.name.trim()).length !== 1 ? "s" : ""}
                    </span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-medium text-gray-700 mb-4">
                Screening Results
              </h2>

              {results.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Shield className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>Results will appear here after screening</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {results.map((result, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border ${
                        result.is_hit
                          ? "border-red-200 bg-red-50"
                          : "border-green-200 bg-green-50"
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          {result.is_hit ? (
                            <AlertTriangle className="w-5 h-5 text-red-600" />
                          ) : (
                            <CheckCircle className="w-5 h-5 text-green-600" />
                          )}
                          <div>
                            <p className="font-medium text-gray-900">
                              {result.screened_name}
                            </p>
                            <p className="text-sm text-gray-500">
                              Screened at{" "}
                              {new Date(result.screened_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <span
                          className={`text-sm font-medium ${
                            result.is_hit ? "text-red-700" : "text-green-700"
                          }`}
                        >
                          {result.is_hit
                            ? `${result.match_count} Match${
                                result.match_count !== 1 ? "es" : ""
                              }`
                            : "Clear"}
                        </span>
                      </div>

                      {/* Match Details */}
                      {result.matches && result.matches.length > 0 && (
                        <div className="mt-4 space-y-3">
                          {result.matches.map((match: SanctionsMatch, mIndex: number) => {
                            const severity = getMatchSeverity(match.score);
                            return (
                              <div
                                key={mIndex}
                                className="bg-white rounded-lg p-3 border border-red-100"
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-gray-900">
                                    {match.original_name}
                                  </span>
                                  <span
                                    className={`text-xs px-2 py-1 rounded-full ${severity.color}`}
                                  >
                                    {match.score.toFixed(1)}% - {severity.label}
                                  </span>
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  <div className="flex items-center space-x-1 text-gray-600">
                                    <Globe className="w-3.5 h-3.5" />
                                    <span>{match.list_type}</span>
                                  </div>
                                  <div className="flex items-center space-x-1 text-gray-600">
                                    {match.entity_type === "individual" ? (
                                      <User className="w-3.5 h-3.5" />
                                    ) : (
                                      <Building className="w-3.5 h-3.5" />
                                    )}
                                    <span className="capitalize">
                                      {match.entity_type}
                                    </span>
                                  </div>
                                </div>
                                {match.programs && match.programs.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1">
                                    {match.programs.map((program, pIndex) => (
                                      <span
                                        key={pIndex}
                                        className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded"
                                      >
                                        {program}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                {match.aliases && match.aliases.length > 0 && (
                                  <div className="mt-2 text-xs text-gray-500">
                                    <span className="font-medium">Also known as: </span>
                                    {match.aliases.join(", ")}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Lists Checked */}
                      <div className="mt-3 flex items-center space-x-2 text-xs text-gray-500">
                        <span>Checked:</span>
                        {result.lists_checked?.map((list, lIndex) => (
                          <span
                            key={lIndex}
                            className="px-2 py-0.5 bg-gray-100 rounded"
                          >
                            {list}
                          </span>
                        ))}
                        <span className="ml-auto">
                          {result.processing_time_ms}ms
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Export Options */}
            {results.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {results.filter((r) => r.is_hit).length} hits out of{" "}
                    {results.length} screened
                  </span>
                  <button className="flex items-center space-x-2 text-sm text-indigo-600 hover:text-indigo-700">
                    <Download className="w-4 h-4" />
                    <span>Export Report</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

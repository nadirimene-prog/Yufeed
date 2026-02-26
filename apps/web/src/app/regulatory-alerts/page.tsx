"use client";

/**
 * Compatibility route for document/regulatory alerts.
 * Intentionally kept on legacy styling for now while AML investigation flows
 * are prioritized on /transaction-alerts and /dashboard.
 */

import { useState } from "react";
import {
  Bell,
  AlertTriangle,
  FileText,
  ExternalLink,
  Check,
  Clock,
  Search,
  CheckSquare,
  Square,
  X,
  Archive,
} from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { useAlerts } from "@/hooks/queries/useAlertData";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { cn } from "@/lib/utils";

// Alert type is defined by the API and used via the hook's return type

type AlertFilter = "all" | "new_doc" | "updated_doc" | "new_version";

export default function AlertsPage() {
  const { data: alerts = [], isLoading, error } = useAlerts();
  const [filter, setFilter] = useState<AlertFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set());
  const [processingBulk, setProcessingBulk] = useState(false);

  const getAlertConfig = (eventType: string) => {
    const configs = {
      new_doc: {
        title: "New Document",
        color: "text-green-600 ",
        bgColor: "bg-green-100 ",
        borderColor: "border-green-200 ",
        status: "success" as const,
        icon: FileText,
      },
      updated_doc: {
        title: "Document Updated",
        color: "text-blue-600 ",
        bgColor: "bg-blue-100 ",
        borderColor: "border-blue-200 ",
        status: "active" as const,
        icon: Bell,
      },
      new_version: {
        title: "New Version",
        color: "text-yellow-600 ",
        bgColor: "bg-yellow-100 ",
        borderColor: "border-yellow-200 ",
        status: "warning" as const,
        icon: AlertTriangle,
      },
    };
    return configs[eventType as keyof typeof configs] || configs.updated_doc;
  };

  const filteredAlerts = alerts.filter((alert) => {
    const matchesFilter = filter === "all" || alert.event_type === filter;
    const matchesSearch =
      !searchQuery ||
      alert.document?.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.document?.celex.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const alertStats = {
    total: alerts.length,
    new_doc: alerts.filter((a) => a.event_type === "new_doc").length,
    updated_doc: alerts.filter((a) => a.event_type === "updated_doc").length,
    new_version: alerts.filter((a) => a.event_type === "new_version").length,
  };

  const toggleSelectAll = () => {
    if (selectedAlerts.size === filteredAlerts.length) {
      setSelectedAlerts(new Set());
    } else {
      setSelectedAlerts(new Set(filteredAlerts.map((a) => a.id)));
    }
  };

  const toggleSelectAlert = (id: number) => {
    const newSelected = new Set(selectedAlerts);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedAlerts(newSelected);
  };

  const handleBulkAcknowledge = async () => {
    setProcessingBulk(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // console.log('Acknowledged alerts:', Array.from(selectedAlerts));
      setSelectedAlerts(new Set());
    } finally {
      setProcessingBulk(false);
    }
  };

  const handleBulkArchive = async () => {
    setProcessingBulk(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // console.log('Archived alerts:', Array.from(selectedAlerts));
      setSelectedAlerts(new Set());
    } finally {
      setProcessingBulk(false);
    }
  };

  return (
    <LoadingBoundary
      loading={isLoading}
      error={error}
      isEmpty={!alerts || alerts.length === 0}
      emptyMessage="No alerts yet"
      emptyDescription="New alerts will appear here when documents are updated"
    >
      <div className="space-y-8 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 ">
              Alerts
            </h1>
            <p className="mt-2 text-slate-600 ">
              Recent updates from your watchlists
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500 ">
            <Clock className="h-4 w-4" />
            <span>{alerts.length} total alerts</span>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="bg-white  rounded-lg border border-slate-200  p-1 inline-flex gap-1">
          <button
            onClick={() => setFilter("all")}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-md transition-colors",
              filter === "all"
                ? "bg-slate-100  text-slate-900 "
                : "text-slate-600  hover:text-slate-900 ",
            )}
          >
            All ({alertStats.total})
          </button>
          <button
            onClick={() => setFilter("new_doc")}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-md transition-colors",
              filter === "new_doc"
                ? "bg-green-100  text-green-700 "
                : "text-slate-600  hover:text-slate-900 ",
            )}
          >
            New Documents ({alertStats.new_doc})
          </button>
          <button
            onClick={() => setFilter("updated_doc")}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-md transition-colors",
              filter === "updated_doc"
                ? "bg-blue-100  text-blue-700 "
                : "text-slate-600  hover:text-slate-900 ",
            )}
          >
            Updated ({alertStats.updated_doc})
          </button>
          <button
            onClick={() => setFilter("new_version")}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-md transition-colors",
              filter === "new_version"
                ? "bg-yellow-100  text-yellow-700 "
                : "text-slate-600  hover:text-slate-900 ",
            )}
          >
            New Versions ({alertStats.new_version})
          </button>
        </div>

        {/* Bulk Actions Bar */}
        {selectedAlerts.size > 0 && (
          <div className="bg-blue-50  border border-blue-200  rounded-lg p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckSquare className="h-5 w-5 text-blue-600 " />
              <span className="font-medium text-blue-900 ">
                {selectedAlerts.size} alert
                {selectedAlerts.size === 1 ? "" : "s"} selected
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkAcknowledge}
                disabled={processingBulk}
                className="px-4 py-2 text-sm font-medium text-blue-700  hover:bg-blue-100  rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Check className="h-4 w-4" />
                Acknowledge All
              </button>
              <button
                onClick={handleBulkArchive}
                disabled={processingBulk}
                className="px-4 py-2 text-sm font-medium text-blue-700  hover:bg-blue-100  rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Archive className="h-4 w-4" />
                Archive
              </button>
              <button
                onClick={() => setSelectedAlerts(new Set())}
                className="px-3 py-2 text-slate-600  hover:bg-slate-100  rounded-md transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
          <input
            type="text"
            placeholder="Search alerts by document title or CELEX..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-white  border border-slate-200  rounded-lg text-slate-900  placeholder-slate-500  focus:outline-none focus:ring-2 focus:ring-blue-500 "
          />
        </div>

        {/* Alerts List */}
        <div className="space-y-3">
          {filteredAlerts.length > 0 && (
            <div className="flex items-center gap-3 px-2 py-2">
              <button
                onClick={toggleSelectAll}
                className="p-1 hover:bg-slate-100  rounded transition-colors"
              >
                {selectedAlerts.size === filteredAlerts.length ? (
                  <CheckSquare className="h-5 w-5 text-blue-600 " />
                ) : (
                  <Square className="h-5 w-5 text-slate-400" />
                )}
              </button>
              <span className="text-sm text-slate-600 ">
                {selectedAlerts.size > 0
                  ? `${selectedAlerts.size} selected`
                  : "Select all"}
              </span>
            </div>
          )}

          {filteredAlerts.length === 0 ? (
            <EmptyState
              variant={searchQuery ? "no-results" : "no-data"}
              title={searchQuery ? "No matching alerts" : "No alerts yet"}
              description={
                searchQuery
                  ? "Try adjusting your search criteria"
                  : "New alerts will appear here when documents are updated"
              }
            />
          ) : (
            filteredAlerts.map((alert) => {
              const config = getAlertConfig(alert.event_type);
              const Icon = config.icon;

              const isSelected = selectedAlerts.has(alert.id);

              return (
                <div
                  key={alert.id}
                  className={cn(
                    "group bg-white  rounded-lg border shadow-sm hover:shadow-md transition-all",
                    isSelected
                      ? "border-blue-500  bg-blue-50/50 "
                      : "border-slate-200  hover:border-slate-300 ",
                  )}
                >
                  <div className="p-6">
                    <div className="flex gap-4">
                      {/* Checkbox */}
                      <div className="flex-shrink-0 pt-1">
                        <button
                          onClick={() => toggleSelectAlert(alert.id)}
                          className="p-1 hover:bg-slate-100  rounded transition-colors"
                        >
                          {isSelected ? (
                            <CheckSquare className="h-5 w-5 text-blue-600 " />
                          ) : (
                            <Square className="h-5 w-5 text-slate-400" />
                          )}
                        </button>
                      </div>

                      {/* Icon */}
                      <div className="flex-shrink-0">
                        <div
                          className={cn(
                            "rounded-lg p-3",
                            config.bgColor,
                            config.borderColor,
                            "border",
                          )}
                        >
                          <Icon className={cn("h-6 w-6", config.color)} />
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-slate-900 ">
                              {config.title}
                            </h3>
                            <StatusIndicator status={config.status} size="sm" />
                          </div>
                          <time className="text-sm text-slate-500  whitespace-nowrap">
                            {format(
                              new Date(alert.detected_at),
                              "MMM d, h:mm a",
                            )}
                          </time>
                        </div>

                        {alert.document && (
                          <>
                            <p className="text-slate-900  mb-2 line-clamp-2">
                              {alert.document.title}
                            </p>
                            <div className="flex items-center justify-between">
                              <p className="text-xs text-slate-500  font-mono">
                                {alert.document.celex}
                              </p>
                              <Link
                                href={`/doc/${alert.document.celex}`}
                                className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700   transition-colors"
                              >
                                View Document
                                <ExternalLink className="h-3 w-3" />
                              </Link>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </LoadingBoundary>
  );
}

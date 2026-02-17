"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Plus, Search, Loader2, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { logger } from "@/lib/logger";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import RiskHeatMap from "@/components/compliance/RiskHeatMap";
import RiskEntryCard from "@/components/compliance/RiskEntryCard";
import RiskCategoryTree from "@/components/compliance/RiskCategoryTree";
import {
  getRiskCategoryTree,
  getRiskEntries,
  getRiskHeatmap,
  getRiskMap,
  createRiskEntry,
} from "@/lib/compliance-api";
import type {
  RiskCategoryTree as RiskCategoryTreeType,
  RiskEntry,
  RiskHeatMapData,
  RiskMapSummary,
  RiskEntryCreate,
  RiskLevelType,
  MitigationStatus,
} from "@/types/compliance";

export default function RiskMapPage() {
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<RiskCategoryTreeType[]>([]);
  const [entries, setEntries] = useState<RiskEntry[]>([]);
  const [heatmapData, setHeatmapData] = useState<RiskHeatMapData | null>(null);
  const [riskMapSummary, setRiskMapSummary] = useState<RiskMapSummary | null>(
    null,
  );

  const [selectedCategory, setSelectedCategory] =
    useState<RiskCategoryTreeType | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLevel, setFilterLevel] = useState<RiskLevelType | "">("");
  const [filterStatus, setFilterStatus] = useState<MitigationStatus | "">("");

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<RiskEntry | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadEntries();
  }, [selectedCategory, filterLevel, filterStatus, searchQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadData = async () => {
    setLoading(true);
    try {
      const [categoriesRes, heatmapRes, summaryRes] = await Promise.all([
        getRiskCategoryTree(),
        getRiskHeatmap(),
        getRiskMap(),
      ]);
      setCategories(categoriesRes.items);
      setHeatmapData(heatmapRes);
      setRiskMapSummary(summaryRes);
    } catch (err) {
      logger.error("Failed to load risk map data:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadEntries = async () => {
    try {
      const params: Record<string, unknown> = { limit: 50 };
      if (selectedCategory) {
        params.category_id = selectedCategory.id;
      }
      if (filterLevel) {
        params.inherent_risk_level = filterLevel;
      }
      if (filterStatus) {
        params.mitigation_status = filterStatus;
      }
      if (searchQuery) {
        params.q = searchQuery;
      }
      const res = await getRiskEntries(
        params as Parameters<typeof getRiskEntries>[0],
      );
      setEntries(res.items);
    } catch (err) {
      logger.error("Failed to load risk entries:", err);
    }
  };

  const handleCreateEntry = async (data: RiskEntryCreate) => {
    try {
      await createRiskEntry(data);
      setShowCreateModal(false);
      loadEntries();
      loadData();
    } catch (err) {
      logger.error("Failed to create risk entry:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-[#6d5acd]" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="h-6 w-6 text-[#6d5acd]" />
            Risk Map
          </h1>
          <p className="text-white/60 mt-1">
            Visualize and manage business risks linked to regulatory obligations
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          className="bg-[#6d5acd] hover:bg-[#5d4abd]"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Risk Entry
        </Button>
      </div>

      {/* Summary Cards */}
      {riskMapSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard
            label="Total Risks"
            value={riskMapSummary.total_entries}
            icon={<AlertTriangle className="h-4 w-4" />}
            color="bg-[#6d5acd]/20 text-[#6d5acd]"
          />
          <SummaryCard
            label="Critical"
            value={riskMapSummary.by_inherent_level.critical || 0}
            icon={<AlertTriangle className="h-4 w-4" />}
            color="bg-red-500/20 text-red-400"
          />
          <SummaryCard
            label="High"
            value={riskMapSummary.by_inherent_level.high || 0}
            icon={<AlertTriangle className="h-4 w-4" />}
            color="bg-orange-500/20 text-orange-400"
          />
          <SummaryCard
            label="Not Mitigated"
            value={riskMapSummary.by_mitigation_status.not_started || 0}
            icon={<AlertTriangle className="h-4 w-4" />}
            color="bg-amber-500/20 text-amber-400"
          />
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar - Category Tree */}
        <GlassCard className="lg:col-span-1">
          <h2 className="text-sm font-semibold text-white/70 mb-4">
            Risk Categories
          </h2>
          <RiskCategoryTree
            categories={categories}
            selectedCategoryId={selectedCategory?.id}
            onSelectCategory={(cat) => setSelectedCategory(cat || null)}
          />
        </GlassCard>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Heat Map */}
          <GlassCard>
            <h2 className="text-lg font-semibold text-white mb-4">
              Risk Heat Map
            </h2>
            {heatmapData && (
              <RiskHeatMap
                cells={heatmapData.cells}
                onCellClick={(cell) => {
                  // TODO: Implement filtering entries by likelihood/impact
                  // This would require adding likelihood/impact filters to the UI
                  // For now, selecting a cell could scroll to or highlight matching entries
                  if (cell.count > 0) {
                    // Could filter entries here when filters are implemented
                  }
                }}
              />
            )}
          </GlassCard>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/40" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search risks..."
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
              />
            </div>

            {/* Risk Level Filter */}
            <select
              value={filterLevel}
              onChange={(e) =>
                setFilterLevel(e.target.value as RiskLevelType | "")
              }
              className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
            >
              <option value="">All Risk Levels</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Mitigation Status Filter */}
            <select
              value={filterStatus}
              onChange={(e) =>
                setFilterStatus(e.target.value as MitigationStatus | "")
              }
              className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
            >
              <option value="">All Statuses</option>
              <option value="not_started">Not Started</option>
              <option value="in_progress">In Progress</option>
              <option value="implemented">Implemented</option>
              <option value="monitored">Monitored</option>
            </select>

            {/* Clear Filters */}
            {(filterLevel || filterStatus || searchQuery) && (
              <button
                onClick={() => {
                  setFilterLevel("");
                  setFilterStatus("");
                  setSearchQuery("");
                }}
                className="px-3 py-2 text-sm text-white/60 hover:text-white"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Risk Entries Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {entries.length === 0 ? (
              <div className="col-span-full text-center py-12 text-white/50">
                No risk entries found
              </div>
            ) : (
              entries.map((entry) => (
                <RiskEntryCard
                  key={entry.id}
                  risk={entry}
                  onClick={() => setSelectedEntry(entry)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Create Risk Entry Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateRiskEntryModal
            categories={categories}
            onClose={() => setShowCreateModal(false)}
            onSubmit={handleCreateEntry}
          />
        )}
      </AnimatePresence>

      {/* Risk Entry Detail Modal */}
      <AnimatePresence>
        {selectedEntry && (
          <RiskEntryDetailModal
            entry={selectedEntry}
            onClose={() => setSelectedEntry(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div
      className={cn(
        "p-4 rounded-xl border border-white/10",
        color.replace("text-", "border-").replace("/20", "/30"),
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("p-1.5 rounded-lg", color)}>{icon}</div>
        <span className="text-sm text-white/70">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function CreateRiskEntryModal({
  categories,
  onClose,
  onSubmit,
}: {
  categories: RiskCategoryTreeType[];
  onClose: () => void;
  onSubmit: (data: RiskEntryCreate) => Promise<void>;
}) {
  const [formData, setFormData] = useState<RiskEntryCreate>({
    category_id: categories[0]?.id || 0,
    name: "",
    description: "",
    inherent_risk_level: "medium",
    residual_risk_level: "medium",
    mitigation_status: "not_started",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
    } finally {
      setIsSubmitting(false);
    }
  };

  const flatCategories = React.useMemo(() => {
    const flatten = (
      cats: RiskCategoryTreeType[],
      depth = 0,
    ): { id: number; name: string; depth: number }[] => {
      const result: { id: number; name: string; depth: number }[] = [];
      for (const cat of cats) {
        result.push({ id: cat.id, name: cat.name, depth });
        if (cat.children.length > 0) {
          result.push(...flatten(cat.children, depth + 1));
        }
      }
      return result;
    };
    return flatten(categories);
  }, [categories]);

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-black/80" onClick={onClose} />
      <motion.div
        className="relative w-full max-w-lg bg-[#0f0f1a] border border-white/10 rounded-xl p-6"
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.95 }}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded hover:bg-white/10"
        >
          <X className="h-5 w-5 text-white/60" />
        </button>

        <h2 className="text-lg font-semibold text-white mb-4">
          Create Risk Entry
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-white/70">
              Category
            </label>
            <select
              value={formData.category_id}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  category_id: parseInt(e.target.value),
                })
              }
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
            >
              {flatCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {"  ".repeat(cat.depth)}
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-white/70">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              required
              placeholder="Risk name..."
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-white/70">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              placeholder="Describe the risk..."
              rows={3}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-white/70">
                Inherent Risk
              </label>
              <select
                value={formData.inherent_risk_level}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    inherent_risk_level: e.target.value as RiskLevelType,
                  })
                }
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-white/70">
                Residual Risk
              </label>
              <select
                value={formData.residual_risk_level}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    residual_risk_level: e.target.value as RiskLevelType,
                  })
                }
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-white/70">
              Mitigation Status
            </label>
            <select
              value={formData.mitigation_status}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  mitigation_status: e.target.value as MitigationStatus,
                })
              }
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
            >
              <option value="not_started">Not Started</option>
              <option value="in_progress">In Progress</option>
              <option value="implemented">Implemented</option>
              <option value="monitored">Monitored</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="border-white/10 text-white/70 hover:bg-white/5"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !formData.name.trim()}
              className="bg-[#6d5acd] hover:bg-[#5d4abd]"
            >
              {isSubmitting && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Create Risk Entry
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

function RiskEntryDetailModal({
  entry,
  onClose,
}: {
  entry: RiskEntry;
  onClose: () => void;
}) {
  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-black/80" onClick={onClose} />
      <motion.div
        className="relative w-full max-w-lg bg-[#0f0f1a] border border-white/10 rounded-xl p-6"
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.95 }}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded hover:bg-white/10"
        >
          <X className="h-5 w-5 text-white/60" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div
            className={cn(
              "p-2 rounded-lg",
              entry.inherent_risk_level === "critical" && "bg-red-500/20",
              entry.inherent_risk_level === "high" && "bg-orange-500/20",
              entry.inherent_risk_level === "medium" && "bg-yellow-500/20",
              entry.inherent_risk_level === "low" && "bg-green-500/20",
            )}
          >
            <AlertTriangle
              className={cn(
                "h-5 w-5",
                entry.inherent_risk_level === "critical" && "text-red-400",
                entry.inherent_risk_level === "high" && "text-orange-400",
                entry.inherent_risk_level === "medium" && "text-yellow-400",
                entry.inherent_risk_level === "low" && "text-green-400",
              )}
            />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">{entry.name}</h2>
            <p className="text-xs text-white/50">{entry.risk_id}</p>
          </div>
        </div>

        {entry.description && (
          <p className="text-sm text-white/70 mb-4">{entry.description}</p>
        )}

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="p-3 rounded-lg bg-white/5">
            <p className="text-xs text-white/50 mb-1">Inherent Risk</p>
            <p className="text-sm font-medium text-white capitalize">
              {entry.inherent_risk_level}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-white/5">
            <p className="text-xs text-white/50 mb-1">Residual Risk</p>
            <p className="text-sm font-medium text-white capitalize">
              {entry.residual_risk_level}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-white/5">
            <p className="text-xs text-white/50 mb-1">Mitigation Status</p>
            <p className="text-sm font-medium text-white capitalize">
              {entry.mitigation_status.replace("_", " ")}
            </p>
          </div>
          <div className="p-3 rounded-lg bg-white/5">
            <p className="text-xs text-white/50 mb-1">Category</p>
            <p className="text-sm font-medium text-white">
              {entry.category_name ?? "N/A"}
            </p>
          </div>
        </div>

        {entry.control_owner && (
          <div className="p-3 rounded-lg bg-white/5 mb-4">
            <p className="text-xs text-white/50 mb-1">Control Owner</p>
            <p className="text-sm font-medium text-white">
              {entry.control_owner}
            </p>
          </div>
        )}

        <div className="flex justify-end">
          <Button
            onClick={onClose}
            variant="outline"
            className="border-white/10 text-white/70 hover:bg-white/5"
          >
            Close
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}

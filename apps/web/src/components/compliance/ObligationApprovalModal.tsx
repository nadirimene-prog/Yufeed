"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Check,
  X,
  FileText,
  AlertTriangle,
  Link as LinkIcon,
  Plus,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  Obligation,
  ObligationApprovalData,
  ObligationStatus,
  Policy,
  PolicySuggestion,
  RiskEntry,
} from "@/types/compliance";
import {
  getPolicies,
  getRiskEntries,
  approveObligation,
  getPolicyTemplateSuggestions,
} from "@/lib/compliance-api";
import { getAuthUserProfile } from "@/lib/auth";
import { logger } from "@/lib/logger";

interface ObligationApprovalModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  obligation: Obligation | null;
  onSuccess?: (updatedObligation: Obligation) => void;
}

const statusOptions: {
  value: ObligationStatus;
  label: string;
  icon: React.ReactNode;
  color: string;
}[] = [
  {
    value: "approved",
    label: "Approve",
    icon: <Check className="h-4 w-4" />,
    color:
      "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20",
  },
  {
    value: "rejected",
    label: "Reject",
    icon: <X className="h-4 w-4" />,
    color: "bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20",
  },
  {
    value: "in_review",
    label: "Send to Review",
    icon: <AlertTriangle className="h-4 w-4" />,
    color:
      "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20",
  },
];

export default function ObligationApprovalModal({
  open,
  onOpenChange,
  obligation,
  onSuccess,
}: ObligationApprovalModalProps) {
  const currentUser = useMemo(() => getAuthUserProfile(), []);
  const [selectedStatus, setSelectedStatus] =
    useState<ObligationStatus>("approved");
  const [note, setNote] = useState("");
  const [linkedPolicyId, setLinkedPolicyId] = useState<number | undefined>();
  const [internalRuleName, setInternalRuleName] = useState("");
  const [internalRuleDescription, setInternalRuleDescription] = useState("");
  const [selectedRiskIds, setSelectedRiskIds] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data for dropdowns
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [riskEntries, setRiskEntries] = useState<RiskEntry[]>([]);
  const [suggestions, setSuggestions] = useState<PolicySuggestion[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const isSelfApprovalBlocked = useMemo(() => {
    if (!obligation?.created_by) return false;
    const actor = obligation.created_by.trim().toLowerCase();
    if (!actor) return false;
    const aliases = [currentUser?.email, currentUser?.userId]
      .filter((value): value is string => typeof value === "string")
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
    return aliases.includes(actor);
  }, [currentUser?.email, currentUser?.userId, obligation?.created_by]);

  const availableStatusOptions = useMemo(
    () =>
      statusOptions.filter(
        (option) => !(isSelfApprovalBlocked && option.value === "approved"),
      ),
    [isSelfApprovalBlocked],
  );

  // Load policies and risk entries when modal opens
  useEffect(() => {
    if (open) {
      setLoadingData(true);
      Promise.all([
        getPolicies({ status: "active,approved", limit: 100 }),
        getRiskEntries({ limit: 100 }),
        obligation
          ? getPolicyTemplateSuggestions(obligation.id, 3)
          : Promise.resolve({ items: [] }),
      ])
        .then(([policiesRes, risksRes, suggestionsRes]) => {
          setPolicies(policiesRes.items);
          setRiskEntries(risksRes.items);
          const sortedSuggestions = [...(suggestionsRes.items || [])].sort(
            (a, b) => (b.confidence ?? 0) - (a.confidence ?? 0),
          );
          setSuggestions(sortedSuggestions);
          if (!obligation?.linked_policy_id && sortedSuggestions.length) {
            setLinkedPolicyId(sortedSuggestions[0].policy_document_id);
          }
        })
        .catch((e) => {
          logger.error("Failed to load obligation modal data:", e);
          setPolicies([]);
          setRiskEntries([]);
          setSuggestions([]);
        })
        .finally(() => setLoadingData(false));

      // Reset form state
      setSelectedStatus(isSelfApprovalBlocked ? "in_review" : "approved");
      setNote("");
      setLinkedPolicyId(obligation?.linked_policy_id);
      setInternalRuleName("");
      setInternalRuleDescription("");
      setSelectedRiskIds([]);
      setError(null);
    }
  }, [open, obligation?.linked_policy_id, isSelfApprovalBlocked]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async () => {
    if (!obligation) return;
    if (isSelfApprovalBlocked && selectedStatus === "approved") {
      setError("4-eyes control: the creator cannot approve this obligation.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const data: ObligationApprovalData = {
      status: selectedStatus,
      note: note.trim() || undefined,
      linked_policy_id: linkedPolicyId,
      create_internal_rule: selectedStatus === "approved",
      internal_rule_name: internalRuleName.trim() || undefined,
      internal_rule_description: internalRuleDescription.trim() || undefined,
      link_risk_entry_ids:
        selectedRiskIds.length > 0 ? selectedRiskIds : undefined,
    };

    try {
      const result = await approveObligation(obligation.id, data);
      onSuccess?.(result);
      onOpenChange(false);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to update obligation";
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleRiskSelection = (riskId: number) => {
    setSelectedRiskIds((prev) =>
      prev.includes(riskId)
        ? prev.filter((id) => id !== riskId)
        : [...prev, riskId],
    );
  };

  const handleLinkSuggestedPolicy = (policyDocumentId: number) => {
    setLinkedPolicyId(policyDocumentId);
  };

  const confidenceBadge = (confidence?: number) => {
    const value = Number(confidence ?? 0);
    if (value >= 0.7) {
      return {
        label: `High ${(value * 100).toFixed(0)}%`,
        className: "bg-emerald-500/20 text-emerald-300 border-emerald-400/30",
      };
    }
    if (value >= 0.45) {
      return {
        label: `Medium ${(value * 100).toFixed(0)}%`,
        className: "bg-amber-500/20 text-amber-300 border-amber-400/30",
      };
    }
    return {
      label: `Low ${(value * 100).toFixed(0)}%`,
      className: "bg-rose-500/20 text-rose-300 border-rose-400/30",
    };
  };

  if (!obligation) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl bg-[#0f0f1a] border-white/10 text-white">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold">
            Review Obligation
          </DialogTitle>
          <DialogDescription className="text-white/60">
            {obligation.obligation_id} -{" "}
            {obligation.article_ref || "No article reference"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Obligation Preview */}
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <p className="text-sm text-white/80 line-clamp-3">
              {obligation.obligation_text}
            </p>
          </div>

          {/* Status Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/70">
              Decision
            </label>
            {isSelfApprovalBlocked && (
              <p className="text-xs text-amber-300">
                4-eyes control active: approval requires a different reviewer.
              </p>
            )}
            <div className="grid grid-cols-3 gap-2">
              {availableStatusOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSelectedStatus(option.value)}
                  className={cn(
                    "flex items-center justify-center gap-2 px-3 py-2 rounded-lg border transition-all",
                    selectedStatus === option.value
                      ? option.color
                      : "bg-white/5 border-white/10 text-white/60 hover:bg-white/10",
                  )}
                >
                  {option.icon}
                  <span className="text-sm font-medium">{option.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Note */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/70">
              Note (optional)
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add a note about this decision..."
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50 resize-none"
              rows={2}
            />
          </div>

          {/* Link to Policy */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/70 flex items-center gap-2">
              <LinkIcon className="h-4 w-4" />
              Link to Policy
            </label>
            <p className="text-xs text-white/50">
              If you don’t choose one, YuFeed will auto-link this obligation to
              the best matching master policy when you approve.
            </p>
            <select
              value={linkedPolicyId || ""}
              onChange={(e) =>
                setLinkedPolicyId(
                  e.target.value ? parseInt(e.target.value) : undefined,
                )
              }
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
              disabled={loadingData}
            >
              <option value="">No policy linked</option>
              {policies.map((policy) => (
                <option key={policy.id} value={policy.id}>
                  {policy.policy_id} - {policy.name}
                </option>
              ))}
            </select>
          </div>

          {/* Suggested Policies */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/70 flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Suggested policies
            </label>
            {loadingData ? (
              <div className="text-xs text-white/50">
                Loading policy suggestions...
              </div>
            ) : suggestions.length ? (
              <div className="space-y-2">
                {suggestions.map((suggestion) => {
                  const confidence = confidenceBadge(suggestion.confidence);
                  return (
                    <div
                      key={suggestion.policy_document_id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="text-sm font-medium text-white">
                            {suggestion.name}
                          </div>
                          <span
                            className={cn(
                              "rounded-full border px-2 py-0.5 text-[10px] font-semibold",
                              confidence.className,
                            )}
                          >
                            {confidence.label}
                          </span>
                          <span className="rounded-full border border-white/20 px-2 py-0.5 text-[10px] text-white/70">
                            {suggestion.match_method === "semantic"
                              ? "AI Semantic"
                              : "Keyword"}
                          </span>
                        </div>
                        <div className="text-[11px] text-white/50">
                          {suggestion.category} • {suggestion.policy_id}
                        </div>
                        {suggestion.reasoning ? (
                          <div className="mt-1 text-[11px] text-white/60 line-clamp-2">
                            {suggestion.reasoning}
                          </div>
                        ) : null}
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          handleLinkSuggestedPolicy(
                            suggestion.policy_document_id,
                          )
                        }
                        disabled={isSubmitting}
                      >
                        Link
                      </Button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-white/50">
                No policy suggestions yet.
              </div>
            )}
          </div>

          {/* Internal Rule (auto-created on approval) */}
          {selectedStatus === "approved" && (
            <div className="space-y-3 p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-sm font-medium text-white/80 flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Internal Rule (auto-created on approval)
              </div>
              <div className="space-y-3">
                <input
                  type="text"
                  value={internalRuleName}
                  onChange={(e) => setInternalRuleName(e.target.value)}
                  placeholder="Rule name (optional)"
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                />
                <textarea
                  value={internalRuleDescription}
                  onChange={(e) => setInternalRuleDescription(e.target.value)}
                  placeholder="Rule description (optional)"
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50 resize-none"
                  rows={2}
                />
              </div>
            </div>
          )}

          {/* Link to Risk Entries */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-white/70 flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Link to Risk Entries (optional)
            </label>
            <div className="max-h-32 overflow-y-auto rounded-lg bg-white/5 border border-white/10 p-2 space-y-1">
              {loadingData ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-white/40" />
                </div>
              ) : riskEntries.length === 0 ? (
                <p className="text-sm text-white/40 text-center py-2">
                  No risk entries available
                </p>
              ) : (
                riskEntries.map((risk) => (
                  <label
                    key={risk.id}
                    className={cn(
                      "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors",
                      selectedRiskIds.includes(risk.id)
                        ? "bg-[#6d5acd]/20"
                        : "hover:bg-white/5",
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={selectedRiskIds.includes(risk.id)}
                      onChange={() => toggleRiskSelection(risk.id)}
                      className="rounded border-white/30 bg-white/10 text-[#6d5acd] focus:ring-[#6d5acd]/50"
                    />
                    <span className="text-sm text-white/80 flex-1 truncate">
                      {risk.name}
                    </span>
                    <span
                      className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        risk.inherent_risk_level === "critical" &&
                          "bg-red-500/20 text-red-400",
                        risk.inherent_risk_level === "high" &&
                          "bg-orange-500/20 text-orange-400",
                        risk.inherent_risk_level === "medium" &&
                          "bg-yellow-500/20 text-yellow-400",
                        risk.inherent_risk_level === "low" &&
                          "bg-green-500/20 text-green-400",
                      )}
                    >
                      {risk.inherent_risk_level}
                    </span>
                  </label>
                ))
              )}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
            className="border-white/10 text-white/70 hover:bg-white/5"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className={cn(
              "transition-colors",
              selectedStatus === "approved" &&
                "bg-emerald-600 hover:bg-emerald-700",
              selectedStatus === "rejected" && "bg-red-600 hover:bg-red-700",
              selectedStatus === "in_review" &&
                "bg-amber-600 hover:bg-amber-700",
            )}
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : null}
            {selectedStatus === "approved"
              ? "Approve Obligation"
              : selectedStatus === "rejected"
                ? "Reject Obligation"
                : "Send to Review"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

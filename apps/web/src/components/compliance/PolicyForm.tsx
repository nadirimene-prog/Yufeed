"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Loader2, Save, X } from "lucide-react";
import type { Policy, PolicyCreate, PolicyUpdate, PolicyStatus } from "@/types/compliance";

interface PolicyFormProps {
    policy?: Policy | null;
    onSubmit: (data: PolicyCreate | PolicyUpdate) => Promise<void>;
    onCancel?: () => void;
    className?: string;
}

const statusOptions: { value: PolicyStatus; label: string }[] = [
    { value: "draft", label: "Draft" },
    { value: "in_review", label: "In Review" },
    { value: "approved", label: "Approved" },
    { value: "active", label: "Active" },
    { value: "retired", label: "Retired" },
];

const languageOptions = [
    { value: "en", label: "English" },
    { value: "fr", label: "French" },
    { value: "de", label: "German" },
    { value: "es", label: "Spanish" },
    { value: "it", label: "Italian" },
];

export default function PolicyForm({
    policy,
    onSubmit,
    onCancel,
    className,
}: PolicyFormProps) {
    const [formData, setFormData] = useState<PolicyCreate>({
        name: "",
        version: "",
        owner: "",
        status: "draft",
        language: "en",
        effective_date: "",
        source_url: "",
        content: "",
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isEditing = !!policy;

    useEffect(() => {
        if (policy) {
            setFormData({
                name: policy.name,
                version: policy.version || "",
                owner: policy.owner || "",
                status: policy.status,
                language: policy.language,
                effective_date: policy.effective_date
                    ? policy.effective_date.split("T")[0]
                    : "",
                source_url: policy.source_url || "",
                content: policy.content || "",
            });
        } else {
            setFormData({
                name: "",
                version: "",
                owner: "",
                status: "draft",
                language: "en",
                effective_date: "",
                source_url: "",
                content: "",
            });
        }
    }, [policy]);

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
    ) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setError(null);

        try {
            const submitData: PolicyCreate | PolicyUpdate = {
                name: formData.name,
                version: formData.version || undefined,
                owner: formData.owner || undefined,
                status: formData.status as PolicyStatus,
                language: formData.language,
                effective_date: formData.effective_date
                    ? new Date(formData.effective_date).toISOString()
                    : undefined,
                source_url: formData.source_url || undefined,
                content: formData.content || undefined,
            };

            await onSubmit(submitData);
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : "Failed to save policy";
            setError(errorMessage);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className={cn("space-y-4", className)}>
            {/* Name */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">
                    Policy Name <span className="text-red-400">*</span>
                </label>
                <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    placeholder="e.g., AML Policy"
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                />
            </div>

            {/* Version and Language */}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-white/70">Version</label>
                    <input
                        type="text"
                        name="version"
                        value={formData.version}
                        onChange={handleChange}
                        placeholder="e.g., 1.0"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                    />
                </div>
                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-white/70">Language</label>
                    <select
                        name="language"
                        value={formData.language}
                        onChange={handleChange}
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                    >
                        {languageOptions.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Owner and Status */}
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-white/70">Owner</label>
                    <input
                        type="text"
                        name="owner"
                        value={formData.owner}
                        onChange={handleChange}
                        placeholder="e.g., compliance@company.com"
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                    />
                </div>
                <div className="space-y-1.5">
                    <label className="text-sm font-medium text-white/70">Status</label>
                    <select
                        name="status"
                        value={formData.status}
                        onChange={handleChange}
                        className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                    >
                        {statusOptions.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Effective Date */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">Effective Date</label>
                <input
                    type="date"
                    name="effective_date"
                    value={formData.effective_date}
                    onChange={handleChange}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                />
            </div>

            {/* External URL */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">
                    External Document URL (Notion, etc.)
                </label>
                <input
                    type="url"
                    name="source_url"
                    value={formData.source_url}
                    onChange={handleChange}
                    placeholder="https://notion.so/..."
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50"
                />
            </div>

            {/* Content */}
            <div className="space-y-1.5">
                <label className="text-sm font-medium text-white/70">Content / Notes</label>
                <textarea
                    name="content"
                    value={formData.content}
                    onChange={handleChange}
                    placeholder="Policy content or summary..."
                    rows={4}
                    className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#6d5acd]/50 resize-none"
                />
            </div>

            {/* Error */}
            {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-4">
                {onCancel && (
                    <Button
                        type="button"
                        variant="outline"
                        onClick={onCancel}
                        disabled={isSubmitting}
                        className="border-white/10 text-white/70 hover:bg-white/5"
                    >
                        <X className="h-4 w-4 mr-2" />
                        Cancel
                    </Button>
                )}
                <Button
                    type="submit"
                    disabled={isSubmitting || !formData.name.trim()}
                    className="bg-[#6d5acd] hover:bg-[#5d4abd] flex-1"
                >
                    {isSubmitting ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                        <Save className="h-4 w-4 mr-2" />
                    )}
                    {isEditing ? "Update Policy" : "Create Policy"}
                </Button>
            </div>
        </form>
    );
}

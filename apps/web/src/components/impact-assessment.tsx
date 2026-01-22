"use client";

import { useState, useEffect } from "react";
import {
    Target, CheckCircle2, Circle, AlertCircle, Clock,
    TrendingUp, Users, Wrench, FileEdit, Play, CheckCheck, Ban
} from "lucide-react";
import {
    analyzeDocumentImpact,
    getImpactAssessment,
    getActionItems,
    updateActionItem,
    type ImpactAssessment as ImpactAssessmentType,
    type ActionItem
} from "@/lib/impact-api";

interface ImpactAssessmentProps {
    celex: string;
}

export default function ImpactAssessmentComponent({ celex }: ImpactAssessmentProps) {
    const [assessment, setAssessment] = useState<ImpactAssessmentType | null>(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadAssessment();
    }, [celex]);

    const loadAssessment = async () => {
        try {
            const data = await getImpactAssessment(celex);
            setAssessment(data);
            setError(null);
        } catch (err: unknown) {
            const error = err as { response?: { status?: number } };
            if (error.response?.status === 404) {
                setError("not_found");
            } else {
                setError("error");
            }
        } finally {
            setLoading(false);
        }
    };

    const handleAnalyze = async () => {
        setAnalyzing(true);
        try {
            await analyzeDocumentImpact(celex, false);
            await loadAssessment();
        } catch (err) {
            alert("Analysis failed. Please try again.");
        } finally {
            setAnalyzing(false);
        }
    };

    const handleUpdateAction = async (actionId: number, updates: Partial<{ status: string; notes: string }>) => {
        try {
            await updateActionItem(actionId, updates);
            await loadAssessment();
        } catch (err) {
            alert("Failed to update action item");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="text-lg">Loading impact assessment...</div>
            </div>
        );
    }

    if (error === "not_found") {
        return (
            <div className="text-center py-12">
                <AlertCircle className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Impact Assessment Yet</h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Generate an AI-powered impact assessment to understand how this regulation affects your operations.
                </p>
                <button
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-semibold"
                >
                    {analyzing ? (
                        <>
                            <Clock className="animate-spin h-5 w-5 mr-2" />
                            Analyzing...
                        </>
                    ) : (
                        <>
                            <Target className="h-5 w-5 mr-2" />
                            Generate Impact Assessment
                        </>
                    )}
                </button>
            </div>
        );
    }

    if (!assessment) {
        return <div className="text-center py-12 text-red-600">Failed to load assessment</div>;
    }

    const impactLevelColors = {
        critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
        high: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
        medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
        low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
        minimal: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
    };

    const statusIcons = {
        not_started: <Circle className="h-4 w-4 text-gray-400" />,
        in_progress: <Play className="h-4 w-4 text-blue-600" />,
        completed: <CheckCircle2 className="h-4 w-4 text-green-600" />,
        blocked: <Ban className="h-4 w-4 text-red-600" />,
        deferred: <Clock className="h-4 w-4 text-orange-600" />,
    };

    const affectedAreas = assessment.affected_areas_json?.areas || [];
    const keyChanges = assessment.key_changes?.changes || [];
    const actionItems = assessment.action_items || [];

    const actionStats = {
        total: actionItems.length,
        completed: actionItems.filter(a => a.status === 'completed').length,
        in_progress: actionItems.filter(a => a.status === 'in_progress').length,
        not_started: actionItems.filter(a => a.status === 'not_started').length,
        blocked: actionItems.filter(a => a.status === 'blocked').length,
    };

    return (
        <div className="space-y-8">
            {/* Executive Summary */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
                <div className="flex items-start gap-4">
                    <div className="flex-shrink-0">
                        <Target className="h-8 w-8 text-blue-600" />
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-3">
                            <h3 className="text-xl font-bold">Impact Assessment</h3>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${impactLevelColors[assessment.overall_impact_level as keyof typeof impactLevelColors]}`}>
                                {assessment.overall_impact_level} Impact
                            </span>
                        </div>
                        {assessment.executive_summary && (
                            <p className="text-gray-700 dark:text-gray-300 text-lg leading-relaxed">
                                {assessment.executive_summary}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <MetricCard
                    icon={<Users className="h-5 w-5" />}
                    label="Affected Areas"
                    value={affectedAreas.length}
                    color="blue"
                />
                <MetricCard
                    icon={<CheckCheck className="h-5 w-5" />}
                    label="Action Items"
                    value={actionStats.total}
                    color="purple"
                />
                <MetricCard
                    icon={<Clock className="h-5 w-5" />}
                    label="Estimated Hours"
                    value={assessment.estimated_effort_hours || 0}
                    color="orange"
                />
                <MetricCard
                    icon={<TrendingUp className="h-5 w-5" />}
                    label="Estimated Cost"
                    value={assessment.estimated_cost ? `€${(assessment.estimated_cost / 1000).toFixed(0)}K` : "TBD"}
                    color="green"
                />
            </div>

            {/* Requirements */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <RequirementCard
                    icon={<Wrench />}
                    label="System Changes"
                    required={assessment.requires_system_changes}
                />
                <RequirementCard
                    icon={<FileEdit />}
                    label="Process Changes"
                    required={assessment.requires_process_changes}
                />
                <RequirementCard
                    icon={<FileEdit />}
                    label="Policy Updates"
                    required={assessment.requires_policy_updates}
                />
            </div>

            {/* Affected Business Areas */}
            {affectedAreas.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold mb-3">Affected Business Areas</h4>
                    <div className="flex flex-wrap gap-2">
                        {affectedAreas.map((area: string) => (
                            <span
                                key={area}
                                className="px-3 py-1 bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200 rounded-full text-sm font-medium capitalize"
                            >
                                {area.replace(/_/g, ' ')}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Key Changes */}
            {keyChanges.length > 0 && (
                <div>
                    <h4 className="text-lg font-semibold mb-3">Key Changes</h4>
                    <ul className="space-y-2">
                        {keyChanges.map((change: string, idx: number) => (
                            <li key={idx} className="flex items-start gap-2">
                                <AlertCircle className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5" />
                                <span className="text-gray-700 dark:text-gray-300">{change}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Action Items */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold">Action Plan ({actionStats.total} items)</h4>
                    <div className="flex gap-2 text-xs">
                        <span className="px-2 py-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                            {actionStats.completed} Completed
                        </span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">
                            {actionStats.in_progress} In Progress
                        </span>
                        <span className="px-2 py-1 bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 rounded">
                            {actionStats.not_started} Not Started
                        </span>
                    </div>
                </div>

                <div className="space-y-3">
                    {actionItems.map((action) => (
                        <ActionItemCard
                            key={action.id}
                            action={action}
                            onUpdate={handleUpdateAction}
                            statusIcon={statusIcons[action.status as keyof typeof statusIcons]}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

interface MetricCardProps {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    color: 'blue' | 'purple' | 'orange' | 'green';
}

function MetricCard({ icon, label, value, color }: MetricCardProps) {
    const colors = {
        blue: "bg-blue-50 dark:bg-blue-900/20 text-blue-600",
        purple: "bg-purple-50 dark:bg-purple-900/20 text-purple-600",
        orange: "bg-orange-50 dark:bg-orange-900/20 text-orange-600",
        green: "bg-green-50 dark:bg-green-900/20 text-green-600",
    };

    return (
        <div className={`${colors[color as keyof typeof colors]} rounded-lg p-4`}>
            <div className="flex items-center gap-2 mb-1">
                {icon}
                <span className="text-xs font-medium opacity-80">{label}</span>
            </div>
            <div className="text-2xl font-bold">{value}</div>
        </div>
    );
}

interface RequirementCardProps {
    icon: React.ReactNode;
    label: string;
    required: boolean;
}

function RequirementCard({ icon, label, required }: RequirementCardProps) {
    return (
        <div className={`rounded-lg p-4 border-2 ${required ? 'border-orange-300 bg-orange-50 dark:bg-orange-900/20' : 'border-gray-200 bg-gray-50 dark:bg-gray-900/20'}`}>
            <div className="flex items-center gap-2">
                <div className={required ? 'text-orange-600' : 'text-gray-400'}>
                    {icon}
                </div>
                <span className="font-medium text-sm">{label}</span>
                {required ? (
                    <CheckCircle2 className="h-5 w-5 text-orange-600 ml-auto" />
                ) : (
                    <Circle className="h-5 w-5 text-gray-300 ml-auto" />
                )}
            </div>
        </div>
    );
}

interface ActionItem {
    id: number;
    title: string;
    priority: 1 | 2 | 3 | 4 | 5;
    status: string;
    deadline: string;
    responsible_party?: string;
    description?: string;
}

interface ActionItemCardProps {
    action: ActionItem;
    onUpdate: (actionId: number, updates: Partial<{ status: string; notes: string }>) => void;
    statusIcon: React.ReactNode;
}

function ActionItemCard({ action, onUpdate, statusIcon }: ActionItemCardProps) {
    const priorityColors = {
        1: "border-l-red-500 bg-red-50/50 dark:bg-red-900/10",
        2: "border-l-orange-500 bg-orange-50/50 dark:bg-orange-900/10",
        3: "border-l-yellow-500 bg-yellow-50/50 dark:bg-yellow-900/10",
        4: "border-l-blue-500 bg-blue-50/50 dark:bg-blue-900/10",
        5: "border-l-gray-500 bg-gray-50/50 dark:bg-gray-900/10",
    };

    const handleStatusChange = (newStatus: string) => {
        onUpdate(action.id, { status: newStatus });
    };

    return (
        <div className={`border-l-4 ${priorityColors[action.priority as keyof typeof priorityColors]} rounded-r-lg p-4`}>
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                        {statusIcon}
                        <h5 className="font-semibold">{action.title}</h5>
                        <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">
                            P{action.priority}
                        </span>
                    </div>
                    {action.description && (
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{action.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span className="capitalize">{action.business_area.replace(/_/g, ' ')}</span>
                        {action.estimated_hours && <span>{action.estimated_hours}h estimated</span>}
                        {action.complexity && <span className="capitalize">{action.complexity}</span>}
                    </div>
                </div>
                <div className="flex-shrink-0">
                    <select
                        value={action.status}
                        onChange={(e) => handleStatusChange(e.target.value)}
                        className="text-sm border border-gray-300 dark:border-gray-700 rounded px-2 py-1 bg-white dark:bg-gray-900"
                    >
                        <option value="not_started">Not Started</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                        <option value="blocked">Blocked</option>
                        <option value="deferred">Deferred</option>
                    </select>
                </div>
            </div>
        </div>
    );
}

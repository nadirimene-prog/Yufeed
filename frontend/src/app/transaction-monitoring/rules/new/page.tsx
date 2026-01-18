"use client";

import { useState } from "react";
import {
    Plus,
    Trash2,
    ChevronDown,
    Code,
    Eye,
    Save,
    TriangleAlert
} from "lucide-react";
import { cn } from "@/lib/utils";

type Operator = "==" | "!=" | ">" | "<" | ">=" | "<=" | "contains" | "in";

interface Condition {
    id: string;
    field: string;
    operator: Operator;
    value: string;
}

interface LogicGroup {
    id: string;
    logic: "AND" | "OR";
    conditions: (Condition | LogicGroup)[];
}

export default function RuleBuilderPage() {
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [severity, setSeverity] = useState("medium");

    const [rootGroup, setRootGroup] = useState<LogicGroup>({
        id: "root",
        logic: "AND",
        conditions: [
            { id: "1", field: "amount", operator: ">", value: "1000" }
        ]
    });

    const [activeTab, setActiveTab] = useState<"builder" | "preview">("builder");

    const addCondition = (groupId: string) => {
        // Logic to add a condition to a specific group would go here
    };

    return (
        <div className="h-[calc(100vh-120px)] flex flex-col gap-6 animate-in fade-in duration-500 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between shrink-0">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Rule Builder</h1>
                    <p className="text-sm text-gray-500">Design advanced logic for transaction monitoring.</p>
                </div>
                <div className="flex gap-3">
                    <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
                        Cancel
                    </button>
                    <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 shadow-sm">
                        <Save className="h-4 w-4" />
                        Save Rule
                    </button>
                </div>
            </div>

            <div className="flex flex-1 gap-6 overflow-hidden">
                {/* Sidebar Info */}
                <div className="w-80 shrink-0 space-y-6 overflow-y-auto pr-2">
                    <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 shadow-sm">
                        <h3 className="font-semibold text-gray-900 dark:text-white">Global Settings</h3>
                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-xs font-bold uppercase tracking-wider text-gray-400">Rule Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g. Unusual High Value Transfer"
                                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-bold uppercase tracking-wider text-gray-400">Severity</label>
                                <select
                                    value={severity}
                                    onChange={(e) => setSeverity(e.target.value)}
                                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900"
                                >
                                    <option value="low">Low</option>
                                    <option value="medium">Medium</option>
                                    <option value="high">High</option>
                                    <option value="critical">Critical</option>
                                </select>
                            </div>
                            <div className="space-y-1.5">
                                <label className="text-xs font-bold uppercase tracking-wider text-gray-400">Description</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    rows={4}
                                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="rounded-xl bg-blue-50 p-4 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30">
                        <div className="flex gap-3">
                            <TriangleAlert className="h-5 w-5 text-blue-600 shrink-0" />
                            <div className="text-sm">
                                <p className="font-semibold text-blue-900 dark:text-blue-100">Pro Tip</p>
                                <p className="text-blue-700/80 dark:text-blue-300">Rules with 'Critical' severity will automatically trigger a block on the transaction.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Editor Section */}
                <div className="flex-1 flex flex-col rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950 shadow-lg overflow-hidden">
                    {/* Tabs */}
                    <div className="flex border-b border-gray-100 dark:border-gray-800 shrink-0">
                        <button
                            onClick={() => setActiveTab('builder')}
                            className={cn(
                                "px-6 py-4 text-sm font-medium transition-all border-b-2",
                                activeTab === 'builder' ? "border-blue-600 text-blue-600 bg-blue-50/20" : "border-transparent text-gray-500 hover:text-gray-700"
                            )}
                        >
                            <div className="flex items-center gap-2">
                                <Eye className="h-4 w-4" />
                                <span>Visual Builder</span>
                            </div>
                        </button>
                        <button
                            onClick={() => setActiveTab('preview')}
                            className={cn(
                                "px-6 py-4 text-sm font-medium transition-all border-b-2",
                                activeTab === 'preview' ? "border-blue-600 text-blue-600 bg-blue-50/20" : "border-transparent text-gray-500 hover:text-gray-700"
                            )}
                        >
                            <div className="flex items-center gap-2">
                                <Code className="h-4 w-4" />
                                <span>JSON Preview</span>
                            </div>
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-12 bg-gray-50/30 dark:bg-gray-900/10">
                        {activeTab === 'builder' ? (
                            <div className="max-w-4xl mx-auto space-y-6">
                                {/* Logic Group */}
                                <div className="relative rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-800 p-8 pt-10">
                                    <div className="absolute -top-4 left-6 flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white uppercase tracking-widest shadow-lg">
                                        {rootGroup.logic}
                                    </div>

                                    <div className="space-y-4">
                                        {rootGroup.conditions.map((condition: any) => (
                                            <div key={condition.id} className="flex items-center gap-3 animate-in slide-in-from-left-4 duration-300">
                                                <div className="h-px w-6 bg-gray-200 dark:bg-gray-800" />
                                                <div className="flex-1 flex items-center gap-4 p-4 rounded-xl border border-gray-100 bg-white dark:border-gray-800 dark:bg-gray-950 shadow-sm">
                                                    <select className="bg-transparent text-sm font-medium outline-none">
                                                        <option value="amount">Amount</option>
                                                        <option value="currency">Currency</option>
                                                        <option value="country_code">Country Code</option>
                                                        <option value="user_id">User ID</option>
                                                    </select>
                                                    <span className="text-gray-300">/</span>
                                                    <select className="bg-transparent text-sm font-bold text-blue-600 outline-none">
                                                        <option value=">">{'>'}</option>
                                                        <option value="==">is equal to</option>
                                                        <option value="contains">contains</option>
                                                    </select>
                                                    <input
                                                        type="text"
                                                        value={condition.value}
                                                        className="flex-1 bg-transparent text-sm outline-none px-2"
                                                        placeholder="Value..."
                                                    />
                                                    <button className="text-gray-300 hover:text-red-500 transition-colors">
                                                        <Trash2 className="h-4 w-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="mt-8 flex items-center gap-4">
                                        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:border-blue-200 hover:bg-blue-50/30 transition-all dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
                                            <Plus className="h-3.5 w-3.5" />
                                            ADD CONDITION
                                        </button>
                                        <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:border-blue-200 hover:bg-blue-50/30 transition-all dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
                                            <Plus className="h-3.5 w-3.5" />
                                            ADD GROUP
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="h-full rounded-xl bg-gray-950 p-8 font-mono text-sm text-green-400 overflow-auto border border-gray-800">
                                <pre>{JSON.stringify({
                                    name,
                                    severity,
                                    logic: rootGroup.logic,
                                    conditions: rootGroup.conditions.map(c => ({
                                        field: (c as any).field,
                                        operator: (c as any).operator,
                                        value: (c as any).value
                                    }))
                                }, null, 2)}</pre>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

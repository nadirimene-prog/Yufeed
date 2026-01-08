"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { FileText, Clock, Link as LinkIcon, Download, Eye, Brain, Target } from "lucide-react";
import { RiskBadge, ComplianceDomainBadge } from "./compliance-badges";
import ImpactAssessmentComponent from "./impact-assessment";

interface DocTabsProps {
    document: any;
    celex: string;
}

export default function DocTabs({ document, celex }: DocTabsProps) {
    const [activeTab, setActiveTab] = useState("overview");

    const tabs = [
        { id: "overview", label: "Overview", icon: FileText },
        { id: "compliance", label: "Compliance Analysis", icon: Brain },
        { id: "impact", label: "Impact Assessment", icon: Target },
        { id: "versions", label: "Versions", icon: Clock },
        { id: "relations", label: "Relations", icon: LinkIcon },
        { id: "downloads", label: "Downloads", icon: Download },
    ];

    return (
        <div className="space-y-6">
            <div className="border-b border-gray-200 dark:border-gray-800">
                <nav className="-mb-px flex space-x-8 overflow-x-auto" aria-label="Tabs">
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "group inline-flex items-center border-b-2 px-1 py-4 text-sm font-medium transition-all whitespace-nowrap",
                                    isActive
                                        ? "border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                                        : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400 dark:hover:border-gray-700 dark:hover:text-gray-300"
                                )}
                            >
                                <Icon className={cn("mr-2 h-4 w-4", isActive ? "text-blue-500" : "text-gray-400 group-hover:text-gray-500")} />
                                {tab.label}
                            </button>
                        );
                    })}
                </nav>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                {activeTab === "overview" && (
                    <div className="space-y-4">
                        <h3 className="text-lg font-semibold">Metadata</h3>
                        <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                            <div>
                                <dt className="text-sm font-medium text-gray-500">CELEX</dt>
                                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">{document.celex}</dd>
                            </div>
                            {document.eli && (
                                <div>
                                    <dt className="text-sm font-medium text-gray-500">ELI</dt>
                                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">{document.eli}</dd>
                                </div>
                            )}
                            {document.publication_date && (
                                <div>
                                    <dt className="text-sm font-medium text-gray-500">Publication Date</dt>
                                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{new Date(document.publication_date).toLocaleDateString()}</dd>
                                </div>
                            )}
                            {document.entry_into_force_date && (
                                <div>
                                    <dt className="text-sm font-medium text-gray-500">Entry Into Force</dt>
                                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{new Date(document.entry_into_force_date).toLocaleDateString()}</dd>
                                </div>
                            )}
                            <div>
                                <dt className="text-sm font-medium text-gray-500">Status</dt>
                                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{document.status || "Active"}</dd>
                            </div>
                            {document.type && (
                                <div>
                                    <dt className="text-sm font-medium text-gray-500">Document Type</dt>
                                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{document.type}</dd>
                                </div>
                            )}
                            {document.jurisdictional_scope && (
                                <div>
                                    <dt className="text-sm font-medium text-gray-500">Jurisdictional Scope</dt>
                                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{document.jurisdictional_scope}</dd>
                                </div>
                            )}
                            {document.last_modified && (
                                <div>
                                    <dt className="text-sm font-medium text-gray-500">Last Modified</dt>
                                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{new Date(document.last_modified).toLocaleDateString()}</dd>
                                </div>
                            )}
                        </dl>
                    </div>
                )}

                {activeTab === "compliance" && (
                    <div className="space-y-6">
                        {document.analyzed_at ? (
                            <>
                                <div className="flex items-center gap-4">
                                    {document.compliance_domain && <ComplianceDomainBadge domain={document.compliance_domain} />}
                                    {document.risk_level && <RiskBadge level={document.risk_level} />}
                                </div>

                                {document.ai_summary && (
                                    <div>
                                        <h4 className="text-sm font-semibold mb-2">AI Summary</h4>
                                        <p className="text-sm text-gray-700 dark:text-gray-300">{document.ai_summary}</p>
                                    </div>
                                )}

                                {document.implementation_deadline && (
                                    <div>
                                        <h4 className="text-sm font-semibold mb-2">Implementation Deadline</h4>
                                        <p className="text-sm text-gray-700 dark:text-gray-300">{new Date(document.implementation_deadline).toLocaleDateString()}</p>
                                    </div>
                                )}

                                {document.obligations_json && Object.keys(document.obligations_json).length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-semibold mb-2">Key Obligations</h4>
                                        <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 dark:text-gray-300">
                                            {Object.entries(document.obligations_json).map(([key, value]: [string, any]) => (
                                                <li key={key}>{typeof value === 'string' ? value : JSON.stringify(value)}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                <p className="text-xs text-gray-500">
                                    Analyzed on {new Date(document.analyzed_at).toLocaleString()}
                                </p>
                            </>
                        ) : (
                            <div className="text-center py-8">
                                <p className="text-gray-500 mb-4">This document hasn't been analyzed yet.</p>
                                <button className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
                                    Analyze Document
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "impact" && (
                    <ImpactAssessmentComponent celex={celex} />
                )}

                {activeTab === "versions" && (
                    <div className="relative border-l border-gray-200 dark:border-gray-800 ml-3 space-y-8 py-2">
                        <div className="mb-2 ml-6">
                            <span className="flex absolute -left-1.5 justify-center items-center w-3 h-3 bg-blue-600 rounded-full ring-4 ring-white dark:ring-gray-900"></span>
                            <h3 className="flex items-center mb-1 text-lg font-semibold text-gray-900 dark:text-white">Current Version</h3>
                            {document.publication_date && (
                                <time className="block mb-2 text-sm font-normal leading-none text-gray-400 dark:text-gray-500">
                                    Released on {new Date(document.publication_date).toLocaleDateString()}
                                </time>
                            )}
                            <p className="mb-4 text-base font-normal text-gray-500 dark:text-gray-400">Initial adoption/entry into force.</p>
                        </div>
                    </div>
                )}

                {activeTab === "relations" && (
                    <p className="text-gray-500">No related documents found.</p>
                )}

                {activeTab === "downloads" && (
                    <div className="flex gap-4">
                        <a
                            href={`https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:${celex}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-100 dark:ring-gray-700 dark:hover:bg-gray-800"
                        >
                            <Download className="mr-2 h-4 w-4" /> Download PDF (EUR-Lex)
                        </a>
                        <a
                            href={`https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:${celex}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-100 dark:ring-gray-700 dark:hover:bg-gray-800"
                        >
                            <Eye className="mr-2 h-4 w-4" /> View on EUR-Lex
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
}

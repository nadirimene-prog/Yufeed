"use client";

import QueryChat from "@/components/query-chat";
import { Sparkles, Zap, Brain, Target } from "lucide-react";

export default function QueryPage() {
    return (
        <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950">
            <div className="container mx-auto px-4 py-8">
                {/* Header */}
                <div className="max-w-4xl mx-auto mb-8">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl">
                            <Sparkles className="h-6 w-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Ask Yufeed</h1>
                            <p className="text-gray-600 dark:text-gray-400">Natural language query interface powered by AI</p>
                        </div>
                    </div>

                    {/* Features */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <FeatureCard
                            icon={<Brain className="h-5 w-5 text-blue-600" />}
                            title="AI-Powered"
                            description="Uses Claude Sonnet 4 for accurate, context-aware answers"
                        />
                        <FeatureCard
                            icon={<Zap className="h-5 w-5 text-purple-600" />}
                            title="RAG Technology"
                            description="Retrieves relevant documents and generates precise answers"
                        />
                        <FeatureCard
                            icon={<Target className="h-5 w-5 text-green-600" />}
                            title="Source Citations"
                            description="Every answer includes CELEX references for verification"
                        />
                    </div>
                </div>

                {/* Chat Interface */}
                <div className="max-w-5xl mx-auto">
                    <QueryChat />
                </div>

                {/* Tips */}
                <div className="max-w-4xl mx-auto mt-8">
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                        <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">💡 Tips for better results:</h3>
                        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                            <li>• Be specific: &quot;What are the KYC requirements for high-risk customers?&quot; works better than &quot;Tell me about KYC&quot;</li>
                            <li>• Ask about implementation: &quot;How do I implement the 6th AML Directive?&quot;</li>
                            <li>• Request comparisons: &quot;What changed between the 5th and 6th AML Directives?&quot;</li>
                            <li>• Inquire about deadlines: &quot;What are the upcoming compliance deadlines for 2026?&quot;</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
    return (
        <div className="bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
                {icon}
                <h3 className="font-semibold text-sm">{title}</h3>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">{description}</p>
        </div>
    );
}

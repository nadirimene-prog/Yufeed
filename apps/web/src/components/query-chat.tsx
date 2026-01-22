"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, FileText, AlertCircle, Lightbulb, Loader2 } from "lucide-react";
import { askQuestion, type QueryResponse, type QueryRequest } from "@/lib/query-api";
import Link from "next/link";

interface Message {
    role: "user" | "assistant";
    content: string;
    sources?: QueryResponse["sources"];
    confidence?: string;
    followup_questions?: string[];
}

export default function QueryChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput("");
        setError(null);

        // Add user message
        setMessages(prev => [...prev, { role: "user", content: userMessage }]);
        setLoading(true);

        try {
            const request: QueryRequest = {
                query: userMessage,
                max_documents: 5
            };

            const response = await askQuestion(request);

            // Add assistant message
            setMessages(prev => [...prev, {
                role: "assistant",
                content: response.answer,
                sources: response.sources,
                confidence: response.confidence,
                followup_questions: response.followup_questions || []
            }]);

        } catch (err: any) {
            setError(err.response?.data?.detail || "Failed to process query. Please try again.");
            // Remove the user message on error
            setMessages(prev => prev.slice(0, -1));
        } finally {
            setLoading(false);
        }
    };

    const handleSuggestionClick = (suggestion: string) => {
        setInput(suggestion);
    };

    const suggestedQuestions = [
        "What are the new KYC requirements for crypto exchanges?",
        "Show me all AML regulations affecting transaction monitoring",
        "What are the upcoming implementation deadlines?",
        "What changed in sanctions screening in 2025?",
    ];

    return (
        <div className="flex flex-col h-[calc(100vh-200px)] bg-white dark:bg-gray-950 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
            {/* Header */}
            <div className="flex items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                    <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div>
                    <h2 className="text-lg font-semibold">Ask Yufeed</h2>
                    <p className="text-sm text-gray-500">Natural language query interface</p>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                    <div className="text-center py-12">
                        <Sparkles className="h-16 w-16 text-blue-500 mx-auto mb-4" />
                        <h3 className="text-xl font-semibold mb-2">Ask me anything about EU regulations</h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            I can help you understand AML/CFT regulations, compliance requirements, and implementation guidance.
                        </p>
                        <div className="max-w-2xl mx-auto">
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Try asking:</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {suggestedQuestions.map((q, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => handleSuggestionClick(q)}
                                        className="text-left p-3 text-sm bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 transition-colors"
                                    >
                                        <Lightbulb className="h-4 w-4 inline mr-2 text-yellow-500" />
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        {msg.role === "user" ? (
                            <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl px-4 py-2">
                                <p className="text-sm">{msg.content}</p>
                            </div>
                        ) : (
                            <div className="max-w-[90%] space-y-3">
                                <div className="bg-gray-100 dark:bg-gray-900 rounded-2xl px-4 py-3">
                                    <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{msg.content}</p>
                                </div>

                                {/* Confidence Badge */}
                                {msg.confidence && (
                                    <div className="flex items-center gap-2">
                                        <span className={`text-xs px-2 py-1 rounded-full ${
                                            msg.confidence === 'high' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                                            msg.confidence === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                                            'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                                        }`}>
                                            {msg.confidence} confidence
                                        </span>
                                    </div>
                                )}

                                {/* Sources */}
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="space-y-2">
                                        <p className="text-xs font-medium text-gray-500">Sources ({msg.sources.length}):</p>
                                        <div className="space-y-1">
                                            {msg.sources.map((source, sidx) => (
                                                <Link
                                                    key={sidx}
                                                    href={`/doc/${source.celex}`}
                                                    className="flex items-start gap-2 p-2 text-xs bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg hover:border-blue-500 dark:hover:border-blue-500 transition-colors"
                                                >
                                                    <FileText className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
                                                    <div className="flex-1 min-w-0">
                                                        <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                                            {source.title}
                                                        </p>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <span className="text-gray-500 font-mono">{source.celex}</span>
                                                            {source.compliance_domain && (
                                                                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded text-[10px] uppercase">
                                                                    {source.compliance_domain}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </Link>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Follow-up Questions */}
                                {msg.followup_questions && msg.followup_questions.length > 0 && (
                                    <div className="space-y-2">
                                        <p className="text-xs font-medium text-gray-500">You might also ask:</p>
                                        <div className="flex flex-wrap gap-2">
                                            {msg.followup_questions.map((q, qidx) => (
                                                <button
                                                    key={qidx}
                                                    onClick={() => handleSuggestionClick(q)}
                                                    className="text-xs px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                                                >
                                                    {q}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-gray-100 dark:bg-gray-900 rounded-2xl px-4 py-3">
                            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Analyzing documents...
                            </div>
                        </div>
                    </div>
                )}

                {error && (
                    <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                        <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-800">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a question about EU regulations..."
                        className="flex-1 px-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || loading}
                        className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                    >
                        <Send className="h-4 w-4" />
                        Send
                    </button>
                </div>
            </form>
        </div>
    );
}

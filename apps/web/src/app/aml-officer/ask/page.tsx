"use client";

/**
 * AI Compliance Q&A Page
 *
 * ChatGPT-style interface for asking compliance questions.
 * Uses RAG to ground answers in EU regulations.
 */

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Brain,
  Send,
  ArrowLeft,
  Sparkles,
  FileText,
  ExternalLink,
  Loader2,
  MessageSquare,
  User,
  RefreshCw,
} from "lucide-react";
import amlOfficerApi, { ComplianceAnswer, Source } from "@/lib/aml-officer-api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  followups?: string[];
  confidence?: string;
  timestamp: Date;
}

const SUGGESTED_QUESTIONS = [
  "What are the CDD requirements for high-risk customers under AMLD 5?",
  "When must we file a Suspicious Activity Report?",
  "What are the beneficial ownership disclosure requirements?",
  "How do we handle PEP screening under EU regulations?",
  "What are the record-keeping requirements for AML?",
  "What thresholds trigger enhanced due diligence?",
];

export default function ComplianceQAPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Build conversation history for context
      const conversationHistory = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await amlOfficerApi.askQuestion({
        question,
        conversation_history: conversationHistory,
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        followups: response.followup_questions,
        confidence: response.confidence,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Failed to get answer:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "I apologize, but I encountered an error processing your question. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(input);
    }
  };

  const clearConversation = () => {
    setMessages([]);
  };

  const getConfidenceColor = (confidence?: string) => {
    switch (confidence) {
      case "high":
        return "text-green-600 bg-green-50";
      case "medium":
        return "text-yellow-600 bg-yellow-50";
      case "low":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/aml-officer"
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-indigo-100 rounded-lg">
                <Brain className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  Compliance Q&A
                </h1>
                <p className="text-sm text-gray-500">
                  Ask questions about EU AML regulations
                </p>
              </div>
            </div>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearConversation}
              className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-8">
          {messages.length === 0 ? (
            // Empty state with suggestions
            <div className="text-center py-12">
              <div className="inline-flex p-4 bg-indigo-100 rounded-full mb-6">
                <Sparkles className="w-12 h-12 text-indigo-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                How can I help you today?
              </h2>
              <p className="text-gray-600 mb-8 max-w-md mx-auto">
                Ask me any question about EU AML/CFT regulations. I&apos;ll provide
                answers grounded in official regulatory documents.
              </p>

              <div className="grid md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {SUGGESTED_QUESTIONS.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => handleSubmit(question)}
                    className="p-4 text-left bg-white border border-gray-200 rounded-xl hover:border-indigo-300 hover:shadow-sm transition"
                  >
                    <MessageSquare className="w-5 h-5 text-indigo-500 mb-2" />
                    <p className="text-sm text-gray-700">{question}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // Conversation
            <div className="space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-3xl ${
                      message.role === "user"
                        ? "bg-indigo-600 text-white rounded-2xl rounded-tr-md px-4 py-3"
                        : "bg-white border border-gray-200 rounded-2xl rounded-tl-md p-4"
                    }`}
                  >
                    {message.role === "assistant" && (
                      <div className="flex items-center space-x-2 mb-3">
                        <Brain className="w-5 h-5 text-indigo-600" />
                        <span className="font-medium text-gray-900">
                          AI AML Officer
                        </span>
                        {message.confidence && (
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full ${getConfidenceColor(
                              message.confidence
                            )}`}
                          >
                            {message.confidence} confidence
                          </span>
                        )}
                      </div>
                    )}

                    <div
                      className={`${
                        message.role === "user" ? "" : "text-gray-700"
                      } whitespace-pre-wrap`}
                    >
                      {message.content}
                    </div>

                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <p className="text-sm font-medium text-gray-700 mb-2">
                          Sources:
                        </p>
                        <div className="space-y-2">
                          {message.sources.map((source, idx) => (
                            <Link
                              key={idx}
                              href={`/doc/${source.celex_id}`}
                              className="flex items-center space-x-2 text-sm text-indigo-600 hover:text-indigo-800"
                            >
                              <FileText className="w-4 h-4" />
                              <span>{source.title || source.celex_id}</span>
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Follow-up suggestions */}
                    {message.followups && message.followups.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <p className="text-sm font-medium text-gray-700 mb-2">
                          Related questions:
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {message.followups.map((followup, idx) => (
                            <button
                              key={idx}
                              onClick={() => handleSubmit(followup)}
                              className="text-sm px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition"
                            >
                              {followup}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-md p-4">
                    <div className="flex items-center space-x-2">
                      <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
                      <span className="text-gray-600">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a compliance question..."
              rows={1}
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              onClick={() => handleSubmit(input)}
              disabled={!input.trim() || loading}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Answers are generated using AI and should be verified against
            official regulatory sources.
          </p>
        </div>
      </div>
    </div>
  );
}

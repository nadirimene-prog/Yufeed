"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Sparkles,
    X,
    Send,
    MessageSquare,
    Minimize2,
    Maximize2,
    Brain,
    Bot
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GlassCard } from "@/components/ui/glass-card";
import { cn } from "@/lib/utils";
import { useCopilot } from "@/components/aml-officer/copilot-context";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
}

export function CopilotWidget() {
    const { pageContext } = useCopilot();
    const [isOpen, setIsOpen] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState<Message[]>([
        {
            id: "welcome",
            role: "assistant",
            content: "Hello. I am your AML Copilot. How can I assist you with your compliance tasks today?",
            timestamp: new Date()
        }
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isOpen]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setIsTyping(true);

        // Mock AI response for now
        setTimeout(() => {
            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: "I've analyzed the request. Based on current parameters, this appears to be a standard inquiry. Would you like me to draft a summary for the case file?",
                timestamp: new Date()
            };
            setMessages(prev => [...prev, aiMsg]);
            setIsTyping(false);
        }, 1500);
    };

    const toggleOpen = () => setIsOpen(!isOpen);

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-4">
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className={cn(
                            "w-[380px] origin-bottom-right",
                            isMinimized ? "h-auto" : "h-[600px]"
                        )}
                    >
                        <GlassCard className="h-full flex flex-col overflow-hidden border-white/10 shadow-2xl backdrop-blur-3xl bg-[#0a0a12]/80">
                            {/* Header */}
                            <div className="flex items-center justify-between p-4 border-b border-white/5 bg-white/[0.02]">
                                <div className="flex items-center gap-2">
                                    <div className="p-1.5 rounded-lg bg-[var(--color-aurora-500)]/20 text-[var(--color-aurora-500)]">
                                        <Brain className="w-4 h-4" />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-white">AI Copilot</h3>
                                        <p className="text-[10px] text-white/50 flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                                            Active
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        onClick={() => setIsMinimized(!isMinimized)}
                                        className="text-white/50 hover:text-white"
                                    >
                                        {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon-sm"
                                        onClick={() => setIsOpen(false)}
                                        className="text-white/50 hover:text-white hover:bg-red-500/10 hover:text-red-400"
                                    >
                                        <X className="w-3.5 h-3.5" />
                                    </Button>
                                </div>
                            </div>

                            {/* Chat Area */}
                            {!isMinimized && (
                                <>
                                    <div
                                        ref={scrollRef}
                                        className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-white/10"
                                    >
                                        {messages.map((msg) => (
                                            <div
                                                key={msg.id}
                                                className={cn(
                                                    "flex gap-3 max-w-[85%]",
                                                    msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
                                                )}
                                            >
                                                <div className={cn(
                                                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs",
                                                    msg.role === "assistant"
                                                        ? "bg-[var(--color-aurora-500)]/10 text-[var(--color-aurora-300)] border border-[var(--color-aurora-500)]/20"
                                                        : "bg-white/10 text-white border border-white/10"
                                                )}>
                                                    {msg.role === "assistant" ? <Bot className="w-4 h-4" /> : "ME"}
                                                </div>
                                                <div className={cn(
                                                    "p-3 rounded-2xl text-sm",
                                                    msg.role === "user"
                                                        ? "bg-[var(--color-primary)] text-white/90 rounded-tr-sm"
                                                        : "bg-white/5 text-white/80 rounded-tl-sm border border-white/5"
                                                )}>
                                                    {msg.content}
                                                </div>
                                            </div>
                                        ))}
                                        {isTyping && (
                                            <div className="flex items-center gap-2 text-xs text-white/30 ml-12">
                                                <Sparkles className="w-3 h-3 animate-spin" />
                                                Thinking...
                                            </div>
                                        )}
                                    </div>

                                    {/* Input Area */}
                                    <div className="p-4 border-t border-white/5 bg-white/[0.01]">
                                        <form
                                            onSubmit={(e) => {
                                                e.preventDefault();
                                                handleSend();
                                            }}
                                            className="relative"
                                        >
                                            const {pageContext} = useCopilot();
                                            // ... existing state ...

                                            // ... handleSend ...

                                            // ... return JSX ...
                                            <Input
                                                value={input}
                                                onChange={(e) => setInput(e.target.value)}
                                                placeholder={pageContext ? "Ask about this page..." : "Ask Copilot..."}
                                                className="pr-10 bg-white/5 border-white/10 focus:border-[var(--color-aurora-500)]/50"
                                            />
                                            <Button
                                                type="submit"
                                                size="icon-sm"
                                                className="absolute right-1 top-1 h-7 w-7 bg-[var(--color-aurora-500)] hover:bg-[var(--color-aurora-600)] text-white"
                                                disabled={!input.trim() || isTyping}
                                            >
                                                <Send className="w-3.5 h-3.5" />
                                            </Button>
                                        </form>
                                        <div className="flex gap-2 mt-2 overflow-x-auto pb-1 no-scrollbar">
                                            {["Summarize Risks", "Draft SAR", "Check Sanctions"].map((suggestion) => (
                                                <button
                                                    key={suggestion}
                                                    onClick={() => setInput(suggestion)}
                                                    className="text-[10px] px-2 py-1 rounded-full bg-white/5 border border-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors whitespace-nowrap"
                                                >
                                                    {suggestion}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </>
                            )}
                        </GlassCard>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Toggle Button (FAB) */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleOpen}
                className={cn(
                    "h-14 w-14 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-300",
                    isOpen
                        ? "bg-white/5 text-white/50 hover:text-white" // Muted when open
                        : "bg-gradient-to-br from-[var(--color-aurora-500)] to-[#00d4ff] text-white shadow-aurora-glow" // Vibrant when closed
                )}
            >
                {isOpen ? <Minimize2 className="w-6 h-6" /> : <Sparkles className="w-6 h-6" />}
            </motion.button>
        </div>
    );
}

export default CopilotWidget;

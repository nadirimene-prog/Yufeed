"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  X,
  Send,
  Minimize2,
  Maximize2,
  Brain,
  Bot,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
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
      content:
        "Hello. I am your AML Copilot. How can I assist you with your compliance tasks today?",
      timestamp: new Date(),
    },
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
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Mock AI response for now
    setTimeout(() => {
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "I've analyzed the request. Based on current parameters, this appears to be a standard inquiry. Would you like me to draft a summary for the case file?",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
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
              isMinimized ? "h-auto" : "h-[600px]",
            )}
          >
            <Card className="h-full flex flex-col overflow-hidden border-border shadow-xl bg-white">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-border bg-slate-50">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
                    <Brain className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">
                      AI Copilot
                    </h3>
                    <p className="text-[10px] text-muted-foreground flex items-center gap-1">
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
                    className="text-muted-foreground hover:text-foreground"
                  >
                    {isMinimized ? (
                      <Maximize2 className="w-3.5 h-3.5" />
                    ) : (
                      <Minimize2 className="w-3.5 h-3.5" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setIsOpen(false)}
                    className="text-muted-foreground hover:text-foreground hover:bg-red-50 hover:text-red-500"
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
                    className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-200"
                  >
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={cn(
                          "flex gap-3 max-w-[85%]",
                          msg.role === "user"
                            ? "ml-auto flex-row-reverse"
                            : "mr-auto",
                        )}
                      >
                        <div
                          className={cn(
                            "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs",
                            msg.role === "assistant"
                              ? "bg-primary/10 text-primary border border-primary/20"
                              : "bg-slate-100 text-slate-600 border border-slate-200",
                          )}
                        >
                          {msg.role === "assistant" ? (
                            <Bot className="w-4 h-4" />
                          ) : (
                            "ME"
                          )}
                        </div>
                        <div
                          className={cn(
                            "p-3 rounded-2xl text-sm",
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground rounded-tr-sm"
                              : "bg-slate-50 text-slate-700 rounded-tl-sm border border-border",
                          )}
                        >
                          {msg.content}
                        </div>
                      </div>
                    ))}
                    {isTyping && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground ml-12">
                        <Sparkles className="w-3 h-3 animate-spin" />
                        Thinking...
                      </div>
                    )}
                  </div>

                  {/* Input Area */}
                  <div className="p-4 border-t border-border bg-white">
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        handleSend();
                      }}
                      className="relative"
                    >
                      <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={
                          pageContext
                            ? "Ask about this page..."
                            : "Ask Copilot..."
                        }
                        className="pr-10 bg-slate-50 border-border focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                      />
                      <Button
                        type="submit"
                        size="icon-sm"
                        className="absolute right-1 top-1 h-7 w-7 bg-primary hover:bg-primary/90 text-primary-foreground shadow-none"
                        disabled={!input.trim() || isTyping}
                      >
                        <Send className="w-3.5 h-3.5" />
                      </Button>
                    </form>
                    <div className="flex gap-2 mt-2 overflow-x-auto pb-1 no-scrollbar">
                      {["Summarize Risks", "Draft SAR", "Check Sanctions"].map(
                        (suggestion) => (
                          <button
                            key={suggestion}
                            onClick={() => setInput(suggestion)}
                            className="text-[10px] px-2 py-1 rounded-full bg-slate-50 border border-border hover:bg-slate-100 text-muted-foreground hover:text-foreground transition-colors whitespace-nowrap"
                          >
                            {suggestion}
                          </button>
                        ),
                      )}
                    </div>
                  </div>
                </>
              )}
            </Card>
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
            ? "bg-slate-100 text-slate-500 hover:text-foreground border border-border" // Muted when open
            : "bg-primary text-primary-foreground", // Vibrant when closed
        )}
      >
        {isOpen ? (
          <Minimize2 className="w-6 h-6" />
        ) : (
          <Sparkles className="w-6 h-6" />
        )}
      </motion.button>
    </div>
  );
}

export default CopilotWidget;

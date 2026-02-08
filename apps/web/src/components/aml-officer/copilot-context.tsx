"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface CopilotContextType {
  pageContext: string;
  setPageContext: (context: string) => void;
  isWidgetOpen: boolean;
  toggleWidget: () => void;
}

const CopilotContext = createContext<CopilotContextType | undefined>(undefined);

export function CopilotProvider({ children }: { children: ReactNode }) {
  const [pageContext, setPageContext] = useState<string>("");
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);

  const toggleWidget = () => setIsWidgetOpen((prev) => !prev);

  return (
    <CopilotContext.Provider
      value={{ pageContext, setPageContext, isWidgetOpen, toggleWidget }}
    >
      {children}
    </CopilotContext.Provider>
  );
}

export function useCopilot() {
  const context = useContext(CopilotContext);
  if (context === undefined) {
    throw new Error("useCopilot must be used within a CopilotProvider");
  }
  return context;
}

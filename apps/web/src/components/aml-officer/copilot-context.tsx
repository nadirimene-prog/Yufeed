"use client";

import {
  createContext,
  useContext,
  useState,
  ReactNode,
  useCallback,
  useMemo,
} from "react";

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

  const toggleWidget = useCallback(() => setIsWidgetOpen((prev) => !prev), []);
  const value = useMemo(
    () => ({ pageContext, setPageContext, isWidgetOpen, toggleWidget }),
    [pageContext, isWidgetOpen, toggleWidget],
  );

  return (
    <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>
  );
}

export function useCopilot() {
  const context = useContext(CopilotContext);
  if (context === undefined) {
    return {
      pageContext: "",
      setPageContext: () => {},
      isWidgetOpen: false,
      toggleWidget: () => {},
    };
  }
  return context;
}

"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button-horizon";
import { CheckCircle2, XCircle, AlertCircle, Info, X } from "lucide-react";

/**
 * Horizon Toast System
 * Accessible, non-intrusive notification system
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Types
   ───────────────────────────────────────────────────────────────────────────── */

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
  updateToast: (id: string, toast: Partial<Toast>) => void;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Toast Context
   ───────────────────────────────────────────────────────────────────────────── */

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Toast Provider
   ───────────────────────────────────────────────────────────────────────────── */

interface ToastProviderProps {
  children: React.ReactNode;
  maxToasts?: number;
  position?:
    | "top-left"
    | "top-right"
    | "bottom-left"
    | "bottom-right"
    | "top-center"
    | "bottom-center";
}

export function ToastProvider({
  children,
  maxToasts = 5,
  position = "bottom-right",
}: ToastProviderProps) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const addToast = React.useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => {
        const newToasts = [...prev, { ...toast, id }];
        return newToasts.slice(-maxToasts);
      });
      return id;
    },
    [maxToasts],
  );

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const updateToast = React.useCallback(
    (id: string, updates: Partial<Toast>) => {
      setToasts((prev) =>
        prev.map((toast) =>
          toast.id === id ? { ...toast, ...updates } : toast,
        ),
      );
    },
    [],
  );

  return (
    <ToastContext.Provider
      value={{ toasts, addToast, removeToast, updateToast }}
    >
      {children}
      <ToastContainer
        toasts={toasts}
        position={position}
        onRemove={removeToast}
      />
    </ToastContext.Provider>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Toast Container
   ───────────────────────────────────────────────────────────────────────────── */

interface ToastContainerProps {
  toasts: Toast[];
  position: ToastProviderProps["position"];
  onRemove: (id: string) => void;
}

const positionClasses = {
  "top-left": "top-4 left-4",
  "top-right": "top-4 right-4",
  "bottom-left": "bottom-4 left-4",
  "bottom-right": "bottom-4 right-4",
  "top-center": "top-4 left-1/2 -translate-x-1/2",
  "bottom-center": "bottom-4 left-1/2 -translate-x-1/2",
};

function ToastContainer({
  toasts,
  position = "bottom-right",
  onRemove,
}: ToastContainerProps) {
  return (
    <div
      className={cn(
        "fixed z-50 flex flex-col gap-2 w-full max-w-sm",
        positionClasses[position] || positionClasses["bottom-right"],
      )}
      role="region"
      aria-live="polite"
      aria-label="Notifications"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
        ))}
      </AnimatePresence>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Toast Item
   ───────────────────────────────────────────────────────────────────────────── */

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

const toastVariants = {
  success: {
    icon: CheckCircle2,
    className: "border-success-500/20 bg-success-500/10",
    iconClassName: "text-success-500",
  },
  error: {
    icon: XCircle,
    className: "border-critical-500/20 bg-critical-500/10",
    iconClassName: "text-critical-500",
  },
  warning: {
    icon: AlertCircle,
    className: "border-warning-500/20 bg-warning-500/10",
    iconClassName: "text-warning-500",
  },
  info: {
    icon: Info,
    className: "border-info-500/20 bg-info-500/10",
    iconClassName: "text-info-500",
  },
};

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const { id, title, description, variant, duration = 5000, action } = toast;
  const config = toastVariants[variant];
  const Icon = config.icon;

  // Auto-dismiss timer
  React.useEffect(() => {
    if (duration === Infinity) return;

    const timer = setTimeout(() => {
      onRemove(id);
    }, duration);

    return () => clearTimeout(timer);
  }, [id, duration, onRemove]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn(
        "relative w-full rounded-lg border p-4 shadow-lg",
        config.className,
      )}
      role="alert"
    >
      <div className="flex gap-3">
        <div className="shrink-0">
          <Icon className={cn("h-5 w-5", config.iconClassName)} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          {description && (
            <p className="mt-1 text-sm text-foreground-secondary">
              {description}
            </p>
          )}
          {action && (
            <div className="mt-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  action.onClick();
                  onRemove(id);
                }}
              >
                {action.label}
              </Button>
            </div>
          )}
        </div>
        <button
          onClick={() => onRemove(id)}
          className="shrink-0 rounded-lg p-1 text-foreground-tertiary hover:bg-white/10 hover:text-foreground transition-colors"
          aria-label="Close notification"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      {duration !== Infinity && (
        <motion.div
          initial={{ scaleX: 1 }}
          animate={{ scaleX: 0 }}
          transition={{ duration: duration / 1000, ease: "linear" }}
          className={cn(
            "absolute bottom-0 left-0 right-0 h-0.5 origin-left",
            config.iconClassName.replace("text-", "bg-"),
          )}
        />
      )}
    </motion.div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Toast Hook Helpers
   ───────────────────────────────────────────────────────────────────────────── */

export function useToastHelpers() {
  const { addToast } = useToast();

  const success = React.useCallback(
    (title: string, description?: string) => {
      addToast({ title, description, variant: "success" });
    },
    [addToast],
  );

  const error = React.useCallback(
    (title: string, description?: string) => {
      addToast({ title, description, variant: "error" });
    },
    [addToast],
  );

  const warning = React.useCallback(
    (title: string, description?: string) => {
      addToast({ title, description, variant: "warning" });
    },
    [addToast],
  );

  const info = React.useCallback(
    (title: string, description?: string) => {
      addToast({ title, description, variant: "info" });
    },
    [addToast],
  );

  const promise = React.useCallback(
    async <T,>(
      promise: Promise<T>,
      {
        loading,
        success,
        error,
      }: {
        loading: string;
        success: string | ((data: T) => string);
        error: string | ((err: Error) => string);
      },
    ) => {
      // Toast id is returned but not needed for simple promise toasts

      const _id = addToast({
        title: loading,
        variant: "info",
        duration: Infinity,
      });

      try {
        const data = await promise;
        const successMessage =
          typeof success === "function" ? success(data) : success;
        // Update to success
        addToast({
          title: successMessage,
          variant: "success",
        });
      } catch (err) {
        const errorMessage =
          typeof error === "function" ? error(err as Error) : error;
        addToast({
          title: errorMessage,
          variant: "error",
        });
      }

      return promise;
    },
    [addToast],
  );

  return { success, error, warning, info, promise };
}

/* ─────────────────────────────────────────────────────────────────────────────
   Standalone Toast Function (for use outside React)
   ───────────────────────────────────────────────────────────────────────────── */

let toastCallback: ((toast: Omit<Toast, "id">) => void) | null = null;

export function setToastCallback(callback: (toast: Omit<Toast, "id">) => void) {
  toastCallback = callback;
}

export function toast(toast: Omit<Toast, "id">) {
  if (toastCallback) {
    toastCallback(toast);
  } else {
    console.warn("Toast called before ToastProvider was initialized");
  }
}

export default ToastProvider;

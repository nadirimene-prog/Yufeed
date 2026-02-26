"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { trapFocus } from "@/lib/focus-trap";
import { Button } from "@/components/ui/button-horizon";
import { X, AlertTriangle } from "lucide-react";

/**
 * Horizon Modal System
 * Accessible dialogs with focus management and animations
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Types
   ───────────────────────────────────────────────────────────────────────────── */

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;

  // Size variants
  size?: "sm" | "md" | "lg" | "xl" | "full";

  // Behavior
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  preventScroll?: boolean;
  returnFocus?: boolean;

  // Callbacks
  onOpen?: () => void;
  onCloseComplete?: () => void;

  // Styling
  className?: string;
  overlayClassName?: string;
  showCloseButton?: boolean;
}

export interface ModalHeaderProps {
  children: React.ReactNode;
  className?: string;
  showCloseButton?: boolean;
  onClose?: () => void;
}

export interface ModalFooterProps {
  children: React.ReactNode;
  className?: string;
  align?: "left" | "center" | "right";
}

export interface ConfirmModalProps extends Omit<ModalProps, "children"> {
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: "default" | "danger";
  loading?: boolean;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Size Classes
   ───────────────────────────────────────────────────────────────────────────── */

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  full: "max-w-full mx-4",
};

/* ─────────────────────────────────────────────────────────────────────────────
   Modal Component
   ───────────────────────────────────────────────────────────────────────────── */

export function Modal({
  isOpen,
  onClose,
  children,
  size = "md",
  closeOnOverlayClick = true,
  closeOnEscape = true,
  preventScroll = true,
  returnFocus = true,
  onOpen,
  onCloseComplete,
  className,
  overlayClassName,
  showCloseButton = true,
}: ModalProps) {
  const modalRef = React.useRef<HTMLDivElement>(null);
  const previousActiveElement = React.useRef<HTMLElement | null>(null);

  // Store previously focused element
  React.useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      onOpen?.();
    }
  }, [isOpen, onOpen]);

  // Handle escape key
  React.useEffect(() => {
    if (!isOpen || !closeOnEscape) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, closeOnEscape, onClose]);

  // Prevent scroll on body
  React.useEffect(() => {
    if (!preventScroll) return;

    if (isOpen) {
      const originalStyle = window.getComputedStyle(document.body).overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = originalStyle;
      };
    }
  }, [isOpen, preventScroll]);

  // Focus trap
  React.useEffect(() => {
    if (!isOpen || !modalRef.current) return;

    const cleanup = trapFocus(modalRef.current, { returnFocus });
    return cleanup;
  }, [isOpen, returnFocus]);

  // Handle overlay click
  const handleOverlayClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget && closeOnOverlayClick) {
      onClose();
    }
  };

  return (
    <AnimatePresence onExitComplete={onCloseComplete}>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "absolute inset-0 bg-overlay-scrim/60",
              overlayClassName,
            )}
            onClick={handleOverlayClick}
            aria-hidden="true"
          />

          {/* Modal */}
          <motion.div
            ref={modalRef}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className={cn(
              "relative w-full mx-4 rounded-xl border border-border bg-background-overlay shadow-2xl",
              sizeClasses[size],
              className,
            )}
            role="dialog"
            aria-modal="true"
            onClick={(e) => e.stopPropagation()}
          >
            {showCloseButton && (
              <button
                onClick={onClose}
                className="absolute right-4 top-4 rounded-lg p-1.5 text-foreground-tertiary transition-colors hover:bg-background-floating hover:text-foreground"
                aria-label="Close dialog"
              >
                <X className="h-5 w-5" />
              </button>
            )}
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Modal Header
   ───────────────────────────────────────────────────────────────────────────── */

export function ModalHeader({
  children,
  className,
  showCloseButton,
  onClose,
}: ModalHeaderProps) {
  return (
    <div className={cn("px-6 py-4 border-b border-border-subtle", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">{children}</div>
        {showCloseButton && onClose && (
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-foreground-tertiary transition-colors hover:bg-background-floating hover:text-foreground"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Modal Title
   ───────────────────────────────────────────────────────────────────────────── */

export function ModalTitle({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h2
      className={cn(
        "text-lg font-display font-semibold text-foreground",
        className,
      )}
    >
      {children}
    </h2>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Modal Description
   ───────────────────────────────────────────────────────────────────────────── */

export function ModalDescription({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p className={cn("mt-1 text-sm text-foreground-secondary", className)}>
      {children}
    </p>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Modal Body
   ───────────────────────────────────────────────────────────────────────────── */

export function ModalBody({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("px-6 py-4 max-h-[60vh] overflow-y-auto", className)}>
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Modal Footer
   ───────────────────────────────────────────────────────────────────────────── */

export function ModalFooter({
  children,
  className,
  align = "right",
}: ModalFooterProps) {
  const alignClass = {
    left: "justify-start",
    center: "justify-center",
    right: "justify-end",
  }[align];

  return (
    <div
      className={cn(
        "px-6 py-4 border-t border-border-subtle flex items-center gap-3",
        alignClass,
        className,
      )}
    >
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Confirm Modal
   ───────────────────────────────────────────────────────────────────────────── */

export function ConfirmModal({
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  variant = "default",
  loading = false,
  ...modalProps
}: ConfirmModalProps) {
  const isDanger = variant === "danger";

  return (
    <Modal {...modalProps} onClose={onCancel} size="sm" showCloseButton={false}>
      <div className="px-6 py-6">
        <div className="flex gap-4">
          {isDanger && (
            <div className="shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-risk-critical/10">
                <AlertTriangle className="h-5 w-5 text-risk-critical" />
              </div>
            </div>
          )}
          <div className="flex-1">
            <h3 className="text-lg font-display font-semibold text-foreground">
              {title}
            </h3>
            <p className="mt-2 text-sm text-foreground-secondary">
              {description}
            </p>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={isDanger ? "destructive" : "primary"}
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Drawer Component (Slide-in panel)
   ───────────────────────────────────────────────────────────────────────────── */

export interface DrawerProps extends Omit<ModalProps, "size"> {
  placement?: "left" | "right" | "top" | "bottom";
  width?: string;
}

export function Drawer({
  placement = "right",
  width = "400px",
  children,
  className,
  ...modalProps
}: DrawerProps) {
  const isHorizontal = placement === "left" || placement === "right";

  const placementClasses = {
    left: "left-0 h-full",
    right: "right-0 h-full",
    top: "top-0 w-full",
    bottom: "bottom-0 w-full",
  }[placement];

  const animationVariants = {
    left: { x: "-100%", y: 0 },
    right: { x: "100%", y: 0 },
    top: { x: 0, y: "-100%" },
    bottom: { x: 0, y: "100%" },
  }[placement];

  return (
    <AnimatePresence>
      {modalProps.isOpen && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-overlay-scrim/60"
            onClick={() =>
              modalProps.closeOnOverlayClick && modalProps.onClose()
            }
          />

          {/* Drawer */}
          <motion.div
            initial={animationVariants}
            animate={{ x: 0, y: 0 }}
            exit={animationVariants}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className={cn(
              "absolute bg-background-overlay border-border shadow-2xl",
              isHorizontal
                ? `w-full max-w-md ${placementClasses}`
                : `h-full max-h-[50vh] ${placementClasses}`,
              placement === "left" || placement === "right"
                ? "border-l"
                : "border-t",
              className,
            )}
            style={isHorizontal ? { width } : undefined}
            role="dialog"
            aria-modal="true"
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

export default Modal;

"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * ═══════════════════════════════════════════════════════════════════
 * INPUT - Horizon Design System
 * Clean inputs with focus ring and professional interactions
 * ═══════════════════════════════════════════════════════════════════
 */

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Input variant */
  variant?: "default" | "outline" | "glass" | "ghost";
  /** Left icon/element */
  leftElement?: React.ReactNode;
  /** Right icon/element */
  rightElement?: React.ReactNode;
  /** Error state */
  error?: boolean;
  /** Error message */
  errorMessage?: string;
  /** Optional id for the error message */
  errorMessageId?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type,
      variant = "outline",
      leftElement,
      rightElement,
      error,
      errorMessage,
      errorMessageId,
      disabled,
      ...props
    },
    ref,
  ) => {
    const resolvedErrorId =
      errorMessageId || (props.id ? `${props.id}-error` : undefined);

    const variantStyles = {
      default: cn(
        "border-border-subtle bg-card",
        "focus:border-primary focus:ring-primary/20",
      ),
      outline: cn(
        "border-border-subtle bg-card",
        "focus:border-primary focus:bg-card",
        "focus:shadow-[0_0_0_3px_rgba(0,82,255,0.1)]",
      ),
      glass: cn(
        "border-border-subtle bg-card",
        "focus:border-primary focus:bg-card",
        "focus:shadow-[0_0_0_3px_rgba(0,82,255,0.1)]",
      ),
      ghost: cn(
        "border-transparent bg-transparent",
        "focus:border-border-subtle focus:bg-muted",
      ),
    };

    return (
      <div className="relative w-full">
        <div className="relative">
          {/* Left element */}
          {leftElement && (
            <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-foreground-tertiary">
              {leftElement}
            </div>
          )}

          {/* Input */}
          <input
            type={type}
            className={cn(
              "flex h-10 w-full rounded-lg border px-3 py-2",
              "text-sm text-foreground placeholder:text-foreground-tertiary",
              "transition-all duration-200 ease-out",
              "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-50",
              variantStyles[variant],
              leftElement && "pl-10",
              rightElement && "pr-10",
              error &&
                "border-risk-critical/50 focus:border-risk-critical focus:ring-risk-critical/20",
              className,
            )}
            ref={ref}
            disabled={disabled}
            {...props}
          />

          {/* Right element */}
          {rightElement && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-tertiary">
              {rightElement}
            </div>
          )}
        </div>

        {/* Error message */}
        {error && errorMessage && (
          <p
            id={resolvedErrorId}
            className="mt-1.5 text-xs text-risk-critical"
            aria-live="polite"
          >
            {errorMessage}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";

/**
 * Search Input - Specialized for search with animated icon
 */
interface SearchInputProps extends Omit<InputProps, "leftElement" | "type"> {
  /** Loading state */
  loading?: boolean;
  /** Shortcut hint text */
  shortcut?: string;
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, loading, shortcut, ...props }, ref) => {
    return (
      <div className="relative">
        <Input
          ref={ref}
          type="search"
          leftElement={
            <motion.svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              animate={loading ? { rotate: 360 } : { rotate: 0 }}
              transition={
                loading ? { duration: 1, repeat: Infinity, ease: "linear" } : {}
              }
            >
              {loading ? (
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              ) : (
                <>
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.3-4.3" />
                </>
              )}
            </motion.svg>
          }
          rightElement={
            shortcut ? (
              <kbd className="hidden h-5 items-center gap-1 rounded border border-border-subtle bg-muted px-1.5 font-mono text-[10px] font-medium text-foreground-tertiary sm:inline-flex">
                {shortcut}
              </kbd>
            ) : undefined
          }
          className={className}
          {...props}
        />
      </div>
    );
  },
);
SearchInput.displayName = "SearchInput";

/**
 * Textarea - Clean styled textarea
 */
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Textarea variant */
  variant?: "default" | "outline" | "glass" | "ghost";
  /** Error state */
  error?: boolean;
  /** Error message */
  errorMessage?: string;
  /** Optional id for the error message */
  errorMessageId?: string;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      variant = "outline",
      error,
      errorMessage,
      errorMessageId,
      ...props
    },
    ref,
  ) => {
    const resolvedErrorId =
      errorMessageId || (props.id ? `${props.id}-error` : undefined);
    const variantStyles = {
      default: cn(
        "border-border-subtle bg-card",
        "focus:border-primary focus:ring-primary/20",
      ),
      outline: cn(
        "border-border-subtle bg-card",
        "focus:border-primary focus:bg-card",
        "focus:shadow-[0_0_0_3px_rgba(0,82,255,0.1)]",
      ),
      glass: cn(
        "border-border-subtle bg-card",
        "focus:border-primary focus:bg-card",
        "focus:shadow-[0_0_0_3px_rgba(0,82,255,0.1)]",
      ),
      ghost: cn(
        "border-transparent bg-transparent",
        "focus:border-border-subtle focus:bg-muted",
      ),
    };

    return (
      <div className="relative w-full">
        <textarea
          className={cn(
            "flex min-h-[80px] w-full rounded-lg border px-3 py-2",
            "text-sm text-foreground placeholder:text-foreground-tertiary",
            "transition-all duration-200 ease-out",
            "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:ring-offset-0",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "resize-none",
            variantStyles[variant],
            error &&
              "border-risk-critical/50 focus:border-risk-critical focus:ring-risk-critical/20",
            className,
          )}
          ref={ref}
          {...props}
        />

        {/* Error message */}
        {error && errorMessage && (
          <p
            id={resolvedErrorId}
            className="mt-1.5 text-xs text-risk-critical"
            aria-live="polite"
          >
            {errorMessage}
          </p>
        )}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";

/**
 * Input Group - For combining inputs with buttons/addons
 */
interface InputGroupProps {
  children: React.ReactNode;
  className?: string;
}

type ClassNameProps = { className?: string };

function InputGroup({ children, className }: InputGroupProps) {
  return (
    <div className={cn("flex", className)}>
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child)) return child;

        const isFirst = index === 0;
        const isLast = index === React.Children.count(children) - 1;

        return React.cloneElement(child as React.ReactElement<ClassNameProps>, {
          className: cn(
            (child as React.ReactElement<ClassNameProps>).props.className,
            !isFirst && "rounded-l-none border-l-0",
            !isLast && "rounded-r-none",
          ),
        });
      })}
    </div>
  );
}

/**
 * Input Addon - Left/right addon for InputGroup
 */
interface InputAddonProps {
  children: React.ReactNode;
  className?: string;
}

function InputAddon({ children, className }: InputAddonProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center px-3 rounded-lg",
        "border border-border-subtle bg-muted",
        "text-sm text-foreground-secondary",
        className,
      )}
    >
      {children}
    </div>
  );
}

export { Input, SearchInput, Textarea, InputGroup, InputAddon };

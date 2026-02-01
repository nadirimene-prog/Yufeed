"use client";

import * as React from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { springs } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * INPUT - Sentinel Design System
 * Glass-styled inputs with focus glow and premium interactions
 * ═══════════════════════════════════════════════════════════════════
 */

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Input variant */
  variant?: "default" | "glass" | "ghost";
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
      variant = "glass",
      leftElement,
      rightElement,
      error,
      errorMessage,
      errorMessageId,
      disabled,
      ...props
    },
    ref
  ) => {
    const [isFocused, setIsFocused] = React.useState(false);
    const resolvedErrorId =
      errorMessageId || (props.id ? `${props.id}-error` : undefined);

    const variantStyles = {
      default: cn(
        "border-white/10 bg-white/5",
        "focus:border-[#6d5acd]/50 focus:ring-[#6d5acd]/20"
      ),
      glass: cn(
        "border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
        "focus:border-[#6d5acd]/40 focus:bg-white/[0.05]",
        "focus:shadow-[0_0_20px_rgba(109,90,205,0.15)]"
      ),
      ghost: cn(
        "border-transparent bg-transparent",
        "focus:bg-white/[0.03] focus:border-white/10"
      ),
    };

    return (
      <div className="relative w-full">
        <div className="relative">
          {/* Left element */}
          {leftElement && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none">
              {leftElement}
            </div>
          )}

          {/* Input */}
          <input
            type={type}
            className={cn(
              "flex h-10 w-full rounded-lg border px-3 py-2",
              "text-sm text-white placeholder:text-white/30",
              "transition-all duration-200 ease-out",
              "focus:outline-none focus:ring-2 focus:ring-offset-0",
              "disabled:cursor-not-allowed disabled:opacity-50",
              variantStyles[variant],
              leftElement && "pl-10",
              rightElement && "pr-10",
              error && "border-[#ff3366]/50 focus:border-[#ff3366] focus:ring-[#ff3366]/20",
              className
            )}
            ref={ref}
            disabled={disabled}
            onFocus={(e) => {
              setIsFocused(true);
              props.onFocus?.(e);
            }}
            onBlur={(e) => {
              setIsFocused(false);
              props.onBlur?.(e);
            }}
            {...props}
          />

          {/* Right element */}
          {rightElement && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40">
              {rightElement}
            </div>
          )}

          {/* Focus glow ring (behind input) */}
          {variant === "glass" && (
            <div
              className={cn(
                "absolute inset-0 rounded-lg pointer-events-none transition-opacity duration-300",
                isFocused ? "opacity-100" : "opacity-0"
              )}
              style={{
                background: "linear-gradient(135deg, rgba(109, 90, 205, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%)",
              }}
            />
          )}
        </div>

        {/* Error message */}
        {error && errorMessage && (
          <p
            id={resolvedErrorId}
            className="mt-1.5 text-xs text-[#ff3366]"
            aria-live="polite"
          >
            {errorMessage}
          </p>
        )}
      </div>
    );
  }
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
              transition={loading ? { duration: 1, repeat: Infinity, ease: "linear" } : {}}
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
              <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-white/10 bg-white/5 px-1.5 font-mono text-[10px] font-medium text-white/30">
                {shortcut}
              </kbd>
            ) : undefined
          }
          className={className}
          {...props}
        />
      </div>
    );
  }
);
SearchInput.displayName = "SearchInput";

/**
 * Textarea - Glass-styled textarea
 */
export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Textarea variant */
  variant?: "default" | "glass" | "ghost";
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
      variant = "glass",
      error,
      errorMessage,
      errorMessageId,
      ...props
    },
    ref
  ) => {
    const resolvedErrorId =
      errorMessageId || (props.id ? `${props.id}-error` : undefined);
    const variantStyles = {
      default: cn(
        "border-white/10 bg-white/5",
        "focus:border-[#6d5acd]/50 focus:ring-[#6d5acd]/20"
      ),
      glass: cn(
        "border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
        "focus:border-[#6d5acd]/40 focus:bg-white/[0.05]",
        "focus:shadow-[0_0_20px_rgba(109,90,205,0.15)]"
      ),
      ghost: cn(
        "border-transparent bg-transparent",
        "focus:bg-white/[0.03] focus:border-white/10"
      ),
    };

    return (
      <div className="relative w-full">
        <textarea
          className={cn(
            "flex min-h-[80px] w-full rounded-lg border px-3 py-2",
            "text-sm text-white placeholder:text-white/30",
            "transition-all duration-200 ease-out",
            "focus:outline-none focus:ring-2 focus:ring-offset-0",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "resize-none",
            variantStyles[variant],
            error && "border-[#ff3366]/50 focus:border-[#ff3366] focus:ring-[#ff3366]/20",
            className
          )}
          ref={ref}
          {...props}
        />

        {/* Error message */}
        {error && errorMessage && (
          <p
            id={resolvedErrorId}
            className="mt-1.5 text-xs text-[#ff3366]"
            aria-live="polite"
          >
            {errorMessage}
          </p>
        )}
      </div>
    );
  }
);
Textarea.displayName = "Textarea";

/**
 * Input Group - For combining inputs with buttons/addons
 */
interface InputGroupProps {
  children: React.ReactNode;
  className?: string;
}

function InputGroup({ children, className }: InputGroupProps) {
  return (
    <div className={cn("flex", className)}>
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child)) return child;

        const isFirst = index === 0;
        const isLast = index === React.Children.count(children) - 1;

        return React.cloneElement(child as React.ReactElement<any>, {
          className: cn(
            (child as React.ReactElement<any>).props.className,
            !isFirst && "rounded-l-none border-l-0",
            !isLast && "rounded-r-none"
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
        "border border-white/[0.08] bg-white/[0.03]",
        "text-sm text-white/50",
        className
      )}
    >
      {children}
    </div>
  );
}

export { Input, SearchInput, Textarea, InputGroup, InputAddon };

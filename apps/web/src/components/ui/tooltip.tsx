"use client";

import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

/**
 * ═══════════════════════════════════════════════════════════════════
 * TOOLTIP - Sentinel Design System
 * Clean tooltips with smooth animations
 * ═══════════════════════════════════════════════════════════════════
 */

const TooltipProvider = TooltipPrimitive.Provider;
const TooltipRoot = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;
const TooltipPortal = TooltipPrimitive.Portal;

interface TooltipContentProps extends React.ComponentPropsWithoutRef<
  typeof TooltipPrimitive.Content
> {
  /** Tooltip variant */
  variant?: "default" | "glass" | "dark";
  /** Show arrow */
  arrow?: boolean;
}

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  TooltipContentProps
>(
  (
    {
      className,
      sideOffset = 4,
      variant = "dark", // Default to dark for high contrast in light theme
      arrow = true,
      children,
      ...props
    },
    ref,
  ) => {
    const variantStyles = {
      default:
        "border-border-subtle bg-popover text-popover-foreground shadow-md",
      glass:
        "border-background/10 bg-foreground/95 text-background backdrop-blur-sm shadow-md", // Deprecated glass, mapped to solid dark
      dark: "border-background/10 bg-foreground text-background shadow-md",
    };

    return (
      <TooltipPrimitive.Content
        ref={ref}
        sideOffset={sideOffset}
        className={cn(
          "z-50 overflow-hidden rounded-md border px-3 py-1.5",
          "text-xs font-medium",
          "animate-in fade-in-0 zoom-in-95",
          "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
          "data-[side=bottom]:slide-in-from-top-2",
          "data-[side=left]:slide-in-from-right-2",
          "data-[side=right]:slide-in-from-left-2",
          "data-[side=top]:slide-in-from-bottom-2",
          variantStyles[variant],
          className,
        )}
        {...props}
      >
        {children}
        {arrow && (
          <TooltipPrimitive.Arrow
            className={cn(
              "fill-current",
              (variant === "glass" || variant === "dark") && "text-foreground",
              variant === "default" && "text-popover",
            )}
          />
        )}
      </TooltipPrimitive.Content>
    );
  },
);
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

/**
 * Simple Tooltip wrapper component
 */
interface TooltipProps {
  /** Tooltip content */
  content: React.ReactNode;
  /** Trigger element */
  children: React.ReactNode;
  /** Tooltip side */
  side?: "top" | "right" | "bottom" | "left";
  /** Tooltip alignment */
  align?: "start" | "center" | "end";
  /** Delay before showing */
  delayDuration?: number;
  /** Tooltip variant */
  variant?: "default" | "glass" | "dark";
  /** Additional className for content */
  className?: string;
  /** Disable tooltip */
  disabled?: boolean;
}

function Tooltip({
  content,
  children,
  side = "top",
  align = "center",
  delayDuration = 200,
  variant = "dark",
  className,
  disabled = false,
}: TooltipProps) {
  if (disabled) {
    return <>{children}</>;
  }

  return (
    <TooltipProvider>
      <TooltipRoot delayDuration={delayDuration}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipPortal>
          <TooltipContent
            side={side}
            align={align}
            variant={variant}
            className={className}
          >
            {content}
          </TooltipContent>
        </TooltipPortal>
      </TooltipRoot>
    </TooltipProvider>
  );
}

/**
 * Info Tooltip - With icon trigger
 */
interface InfoTooltipProps extends Omit<TooltipProps, "children"> {
  /** Icon size */
  iconSize?: "sm" | "md" | "lg";
  /** Icon color */
  iconColor?: string;
}

function InfoTooltip({
  content,
  iconSize = "sm",
  iconColor = "text-muted-foreground",
  ...props
}: InfoTooltipProps) {
  const sizeClasses = {
    sm: "h-3.5 w-3.5",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <Tooltip content={content} {...props}>
      <button
        type="button"
        className={cn(
          "inline-flex items-center justify-center rounded-full",
          "hover:text-foreground transition-colors",
          iconColor,
        )}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={sizeClasses[iconSize]}
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
      </button>
    </Tooltip>
  );
}

/**
 * Tooltip with rich content
 */
interface RichTooltipProps extends Omit<TooltipProps, "content"> {
  /** Tooltip title */
  title: string;
  /** Tooltip description */
  description?: string;
  /** Additional content */
  children: React.ReactNode;
  /** Footer content */
  footer?: React.ReactNode;
}

function RichTooltip({
  title,
  description,
  children,
  footer,
  ...props
}: RichTooltipProps) {
  const resolvedVariant = props.variant ?? "dark";
  const isDarkVariant =
    resolvedVariant === "dark" || resolvedVariant === "glass";

  return (
    <TooltipProvider>
      <TooltipRoot delayDuration={props.delayDuration ?? 200}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipPortal>
          <TooltipContent
            side={props.side}
            align={props.align}
            variant={props.variant}
            className={cn("max-w-xs p-0 overflow-hidden", props.className)}
          >
            <div className="p-3 space-y-1">
              <p className="font-medium">{title}</p>
              {description && (
                <p
                  className={cn(
                    "text-xs",
                    isDarkVariant
                      ? "text-background/70"
                      : "text-foreground-secondary",
                  )}
                >
                  {description}
                </p>
              )}
            </div>
            {footer && (
              <div
                className={cn(
                  "px-3 py-2 border-t",
                  isDarkVariant
                    ? "border-background/10 bg-foreground/70"
                    : "border-border-subtle bg-muted/60",
                )}
              >
                {footer}
              </div>
            )}
          </TooltipContent>
        </TooltipPortal>
      </TooltipRoot>
    </TooltipProvider>
  );
}

/**
 * Keyboard shortcut tooltip
 */
interface ShortcutTooltipProps extends Omit<TooltipProps, "content"> {
  /** Tooltip label */
  label: string;
  /** Keyboard shortcut keys */
  shortcut: string[];
}

function ShortcutTooltip({
  label,
  shortcut,
  children,
  ...props
}: ShortcutTooltipProps) {
  return (
    <Tooltip
      content={
        <div className="flex items-center gap-2">
          <span>{label}</span>
          <div className="flex items-center gap-1">
            {shortcut.map((key, index) => (
              <kbd
                key={index}
                className="inline-flex h-5 min-w-[20px] items-center justify-center rounded border border-background/15 bg-foreground/80 px-1.5 font-mono text-[10px] font-medium text-background"
              >
                {key}
              </kbd>
            ))}
          </div>
        </div>
      }
      {...props}
    >
      {children}
    </Tooltip>
  );
}

export {
  Tooltip,
  InfoTooltip,
  RichTooltip,
  ShortcutTooltip,
  TooltipProvider,
  TooltipRoot,
  TooltipTrigger,
  TooltipContent,
  TooltipPortal,
};

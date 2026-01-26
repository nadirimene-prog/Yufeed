"use client";

import { forwardRef, ReactNode } from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";
import { cardHover, transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * GLASS CARD - Premium glass morphism card component
 * ═══════════════════════════════════════════════════════════════════
 */

export type GlassCardVariant = "surface" | "interactive" | "elevated";
export type GlowIntensity = "none" | "subtle" | "strong";
export type RiskGlow = "critical" | "high" | "medium" | "low" | "clear" | "primary";

interface GlassCardProps extends Omit<HTMLMotionProps<"div">, "children"> {
  /** Visual variant of the card */
  variant?: GlassCardVariant;
  /** Glow effect intensity or risk-based glow */
  glow?: GlowIntensity | RiskGlow;
  /** Enable hover lift and glow effects */
  hover?: boolean;
  /** Custom className */
  className?: string;
  /** Card content */
  children: ReactNode;
  /** Whether to animate on mount */
  animate?: boolean;
}

const glowStyles: Record<RiskGlow, string> = {
  critical: "glow-critical",
  high: "glow-high",
  medium: "glow-medium",
  low: "glow-low",
  clear: "glow-clear",
  primary: "glow-primary",
};

const variantStyles: Record<GlassCardVariant, string> = {
  surface: "glass-surface",
  interactive: "glass-interactive",
  elevated: "glass-elevated",
};

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  (
    {
      variant = "surface",
      glow = "none",
      hover = false,
      animate = true,
      className,
      children,
      ...props
    },
    ref
  ) => {
    // Determine if glow is a risk level or intensity
    const isRiskGlow = ["critical", "high", "medium", "low", "clear", "primary"].includes(glow);
    const glowClass = isRiskGlow ? glowStyles[glow as RiskGlow] : "";

    // Base card styles
    const baseStyles = cn(
      "relative overflow-hidden rounded-xl",
      variantStyles[variant],
      glowClass,
      className
    );

    // If hover is enabled and variant is interactive, use motion
    if (hover || variant === "interactive") {
      return (
        <motion.div
          ref={ref}
          className={baseStyles}
          variants={cardHover}
          initial={animate ? "initial" : false}
          whileHover="hover"
          whileTap="tap"
          {...props}
        >
          {/* Optional inner glow overlay */}
          {glow !== "none" && (
            <div
              className="absolute inset-0 opacity-20 pointer-events-none"
              style={{
                background:
                  "radial-gradient(ellipse at 50% 0%, currentColor 0%, transparent 70%)",
              }}
            />
          )}
          <div className="relative z-10">{children}</div>
        </motion.div>
      );
    }

    // Static card without hover effects
    return (
      <motion.div
        ref={ref}
        className={baseStyles}
        initial={animate ? { opacity: 0, y: 10 } : false}
        animate={animate ? { opacity: 1, y: 0 } : false}
        transition={transitions.default}
        {...props}
      >
        {glow !== "none" && (
          <div
            className="absolute inset-0 opacity-10 pointer-events-none"
            style={{
              background:
                "radial-gradient(ellipse at 50% 0%, currentColor 0%, transparent 70%)",
            }}
          />
        )}
        <div className="relative z-10">{children}</div>
      </motion.div>
    );
  }
);

GlassCard.displayName = "GlassCard";

/**
 * Glass Card Header
 */
interface GlassCardHeaderProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardHeader({ className, children }: GlassCardHeaderProps) {
  return (
    <div
      className={cn(
        "px-6 py-4 border-b border-white/5",
        className
      )}
    >
      {children}
    </div>
  );
}

/**
 * Glass Card Title
 */
interface GlassCardTitleProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardTitle({ className, children }: GlassCardTitleProps) {
  return (
    <h3
      className={cn(
        "text-lg font-semibold text-foreground text-display",
        className
      )}
    >
      {children}
    </h3>
  );
}

/**
 * Glass Card Description
 */
interface GlassCardDescriptionProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardDescription({
  className,
  children,
}: GlassCardDescriptionProps) {
  return (
    <p
      className={cn(
        "text-sm text-muted-foreground mt-1",
        className
      )}
    >
      {children}
    </p>
  );
}

/**
 * Glass Card Content
 */
interface GlassCardContentProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardContent({
  className,
  children,
}: GlassCardContentProps) {
  return <div className={cn("p-6", className)}>{children}</div>;
}

/**
 * Glass Card Footer
 */
interface GlassCardFooterProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardFooter({ className, children }: GlassCardFooterProps) {
  return (
    <div
      className={cn(
        "px-6 py-4 border-t border-white/5 bg-white/[0.02]",
        className
      )}
    >
      {children}
    </div>
  );
}

export default GlassCard;

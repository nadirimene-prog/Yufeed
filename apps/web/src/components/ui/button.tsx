"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { motion, HTMLMotionProps } from "framer-motion";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonPress } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * BUTTON - Sentinel Design System
 * Premium buttons with gradient, glow, and glass variants
 * ═══════════════════════════════════════════════════════════════════
 */

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        // Default - Solid primary
        default:
          "bg-primary text-primary-foreground shadow-md hover:bg-primary/90 hover:shadow-lg active:scale-[0.98]",

        // Destructive - Danger actions
        destructive:
          "bg-destructive text-destructive-foreground shadow-md hover:bg-destructive/90 hover:shadow-lg active:scale-[0.98]",

        // Outline - Bordered
        outline:
          "border border-input bg-transparent shadow-sm hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",

        // Secondary - Muted
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80 active:scale-[0.98]",

        // Ghost - No background
        ghost:
          "hover:bg-accent hover:text-accent-foreground active:scale-[0.98]",

        // Link - Text only
        link: "text-primary underline-offset-4 hover:underline",

        // ═══════════════════════════════════════════════════════════
        // SENTINEL PREMIUM VARIANTS
        // ═══════════════════════════════════════════════════════════

        // Gradient - Aurora gradient background
        gradient:
          "bg-gradient-to-r from-[#6d5acd] to-[#00d4ff] text-white shadow-[0_4px_14px_rgba(109,90,205,0.4)] hover:shadow-[0_6px_20px_rgba(109,90,205,0.5)] hover:scale-[1.02] active:scale-[0.98]",

        // Glow - Primary with glowing shadow
        glow: "bg-primary text-primary-foreground shadow-[0_0_20px_rgba(109,90,205,0.4)] hover:shadow-[0_0_30px_rgba(109,90,205,0.6)] hover:scale-[1.02] active:scale-[0.98]",

        // Glass - Transparent with blur
        glass:
          "bg-white/10 backdrop-blur-md border border-white/20 text-foreground shadow-lg hover:bg-white/15 hover:border-white/30 active:scale-[0.98]",

        // Danger Glow - Red with pulsing glow for critical actions
        "danger-glow":
          "bg-[#ff3366] text-white shadow-[0_0_20px_rgba(255,51,102,0.5)] hover:shadow-[0_0_30px_rgba(255,51,102,0.7)] hover:scale-[1.02] active:scale-[0.98]",

        // Success Glow - Green with glow
        "success-glow":
          "bg-[#06d6a0] text-white shadow-[0_0_20px_rgba(6,214,160,0.4)] hover:shadow-[0_0_30px_rgba(6,214,160,0.6)] hover:scale-[1.02] active:scale-[0.98]",

        // Cyan Accent - Cyan horizon color
        cyan: "bg-[#00d4ff] text-[#0a0a12] shadow-[0_4px_14px_rgba(0,212,255,0.3)] hover:shadow-[0_6px_20px_rgba(0,212,255,0.4)] hover:scale-[1.02] active:scale-[0.98]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6 text-base",
        xl: "h-14 px-8 text-lg",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
        "icon-lg": "h-12 w-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render as a different element */
  asChild?: boolean;
  /** Show loading state */
  loading?: boolean;
  /** Left icon */
  leftIcon?: React.ReactNode;
  /** Right icon */
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    if (asChild) {
      return (
        <Slot
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          {...props}
        >
          {children}
        </Slot>
      );
    }

    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={isDisabled}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : leftIcon ? (
          <span className="shrink-0">{leftIcon}</span>
        ) : null}
        {children}
        {!loading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  },
);
Button.displayName = "Button";

/**
 * Animated Button with Framer Motion
 * Use this for premium interactions
 */
interface AnimatedButtonProps
  extends
    Omit<HTMLMotionProps<"button">, "children">,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children?: React.ReactNode;
}

const AnimatedButton = React.forwardRef<HTMLButtonElement, AnimatedButtonProps>(
  (
    {
      className,
      variant,
      size,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <motion.button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        disabled={isDisabled}
        variants={buttonPress}
        initial="initial"
        whileHover={isDisabled ? undefined : "hover"}
        whileTap={isDisabled ? undefined : "tap"}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : leftIcon ? (
          <span className="shrink-0">{leftIcon}</span>
        ) : null}
        {children}
        {!loading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </motion.button>
    );
  },
);
AnimatedButton.displayName = "AnimatedButton";

/**
 * Icon Button - Square button for icons only
 */
interface IconButtonProps extends ButtonProps {
  "aria-label": string;
}

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ size = "icon", children, ...props }, ref) => {
    return (
      <Button ref={ref} size={size} {...props}>
        {children}
      </Button>
    );
  },
);
IconButton.displayName = "IconButton";

export { Button, AnimatedButton, IconButton, buttonVariants };

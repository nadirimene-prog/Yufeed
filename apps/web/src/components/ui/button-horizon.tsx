"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

/**
 * Horizon Button System
 * Accessible, consistent button components with multiple variants
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Button Variants
   ───────────────────────────────────────────────────────────────────────────── */

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-fast focus-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        /* Primary — Main action */
        primary:
          "bg-primary text-white shadow-sm hover:bg-primary-hover active:bg-primary-active active:scale-[0.98]",

        /* Secondary — Alternative action */
        secondary:
          "bg-bg-overlay text-foreground border border-border-default hover:bg-bg-floating hover:border-border-strong active:scale-[0.98]",

        /* Tertiary — Subtle action */
        tertiary:
          "bg-transparent text-foreground-secondary hover:text-foreground hover:bg-bg-elevated active:bg-bg-overlay",

        /* Ghost — Minimal action */
        ghost: "bg-transparent text-foreground-secondary hover:text-foreground",

        /* Destructive — Dangerous action */
        destructive:
          "bg-critical-600 text-white hover:bg-critical-500 active:bg-critical-700 active:scale-[0.98]",

        /* Accent — Highlighted action */
        accent:
          "bg-secondary text-white hover:bg-secondary-hover active:bg-secondary-active active:scale-[0.98]",

        /* Link — Text button */
        link: "bg-transparent text-primary hover:text-primary-hover underline-offset-4 hover:underline p-0 h-auto",

        /* Glass — Translucent button (for backward compatibility) */
        glass:
          "bg-white/5 backdrop-blur-sm border border-white/10 text-foreground hover:bg-white/10",

        /* Outline — Bordered button (for backward compatibility) */
        outline:
          "bg-transparent border border-border-default text-foreground hover:bg-bg-elevated hover:border-border-strong",

        /* Gradient — Gradient background (for backward compatibility) */
        gradient:
          "bg-gradient-to-r from-primary to-secondary text-white hover:opacity-90",
      },
      size: {
        xs: "h-7 px-2.5 text-xs gap-1.5",
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-5 text-base",
        xl: "h-14 px-6 text-base",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
        "icon-lg": "h-12 w-12",
      },
      width: {
        auto: "",
        full: "w-full",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
      width: "auto",
    },
  },
);

/* ─────────────────────────────────────────────────────────────────────────────
   Button Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      width,
      // asChild is reserved for future polymorphic button implementation
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      asChild = false,
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, width, className }))}
        disabled={isDisabled}
        {...props}
      >
        {loading && (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        )}
        {!loading && leftIcon}
        {children}
        {!loading && rightIcon}
      </button>
    );
  },
);
Button.displayName = "Button";

/* ─────────────────────────────────────────────────────────────────────────────
   Icon Button Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface IconButtonProps
  extends Omit<ButtonProps, "leftIcon" | "rightIcon" | "size"> {
  size?: "sm" | "md" | "lg";
  icon: React.ReactNode;
  label: string;
}

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, size = "md", icon, label, ...props }, ref) => {
    const sizeClass = {
      sm: "h-8 w-8",
      md: "h-10 w-10",
      lg: "h-12 w-12",
    }[size];

    return (
      <Button
        ref={ref}
        className={cn(sizeClass, className)}
        aria-label={label}
        {...props}
      >
        {icon}
      </Button>
    );
  },
);
IconButton.displayName = "IconButton";

/* ─────────────────────────────────────────────────────────────────────────────
   Button Group Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface ButtonGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  attached?: boolean;
}

const ButtonGroup = React.forwardRef<HTMLDivElement, ButtonGroupProps>(
  ({ className, attached = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex",
          attached ? "rounded-lg overflow-hidden" : "gap-2",
          className,
        )}
        role="group"
        {...props}
      >
        {attached
          ? React.Children.map(children, (child, index) => {
              if (!React.isValidElement(child)) return child;

              const isFirst = index === 0;
              const isLast = index === React.Children.count(children) - 1;

              return React.cloneElement(
                child as React.ReactElement<ButtonProps>,
                {
                  className: cn(
                    (child.props as ButtonProps).className,
                    "rounded-none",
                    isFirst && "rounded-l-lg",
                    isLast && "rounded-r-lg",
                    "focus:z-10",
                  ),
                },
              );
            })
          : children}
      </div>
    );
  },
);
ButtonGroup.displayName = "ButtonGroup";

/* ─────────────────────────────────────────────────────────────────────────────
   Animated Button (alias for backward compatibility)
   ───────────────────────────────────────────────────────────────────────────── */

const AnimatedButton = Button;

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export { Button, IconButton, ButtonGroup, buttonVariants, AnimatedButton };

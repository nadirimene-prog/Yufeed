"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { motion, type HTMLMotionProps } from "framer-motion";

/**
 * Horizon Card System
 * Flexible, accessible card components with consistent styling
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Card Variants
   ───────────────────────────────────────────────────────────────────────────── */

const cardVariants = cva("rounded-xl border transition-all duration-fast", {
  variants: {
    variant: {
      default:
        "bg-bg-elevated border-border-subtle hover:border-border-default",
      interactive:
        "bg-bg-elevated border-border-subtle cursor-pointer hover:border-border-strong hover:shadow-md hover:-translate-y-0.5",
      elevated: "bg-bg-overlay border-border-default shadow-md hover:shadow-lg",
      ghost: "bg-transparent border-transparent hover:bg-bg-elevated",
      outlined:
        "bg-transparent border-border-default hover:border-border-strong",
    },
    padding: {
      none: "",
      sm: "p-4",
      md: "p-5",
      lg: "p-6",
      xl: "p-8",
    },
  },
  defaultVariants: {
    variant: "default",
    padding: "md",
  },
});

/* ─────────────────────────────────────────────────────────────────────────────
   Card Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  asChild?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(cardVariants({ variant, padding, className }))}
        {...props}
      />
    );
  },
);
Card.displayName = "Card";

/* ─────────────────────────────────────────────────────────────────────────────
   Card Header
   ───────────────────────────────────────────────────────────────────────────── */

const cardHeaderVariants = cva("flex flex-col gap-1", {
  variants: {
    padding: {
      none: "",
      sm: "p-4 pb-0",
      md: "p-5 pb-0",
      lg: "p-6 pb-0",
      xl: "p-8 pb-0",
    },
  },
  defaultVariants: {
    padding: "md",
  },
});

export interface CardHeaderProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardHeaderVariants> {}

const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardHeaderVariants({ padding, className }))}
      {...props}
    />
  ),
);
CardHeader.displayName = "CardHeader";

/* ─────────────────────────────────────────────────────────────────────────────
   Card Title
   ───────────────────────────────────────────────────────────────────────────── */

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-display font-semibold text-foreground leading-tight",
      className,
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

/* ─────────────────────────────────────────────────────────────────────────────
   Card Description
   ───────────────────────────────────────────────────────────────────────────── */

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-foreground-secondary", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

/* ─────────────────────────────────────────────────────────────────────────────
   Card Content
   ───────────────────────────────────────────────────────────────────────────── */

const cardContentVariants = cva("", {
  variants: {
    padding: {
      none: "",
      sm: "p-4",
      md: "p-5",
      lg: "p-6",
      xl: "p-8",
    },
  },
  defaultVariants: {
    padding: "md",
  },
});

export interface CardContentProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardContentVariants> {}

const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardContentVariants({ padding, className }))}
      {...props}
    />
  ),
);
CardContent.displayName = "CardContent";

/* ─────────────────────────────────────────────────────────────────────────────
   Card Footer
   ───────────────────────────────────────────────────────────────────────────── */

const cardFooterVariants = cva("flex items-center gap-3", {
  variants: {
    padding: {
      none: "",
      sm: "p-4 pt-0",
      md: "p-5 pt-0",
      lg: "p-6 pt-0",
      xl: "p-8 pt-0",
    },
  },
  defaultVariants: {
    padding: "md",
  },
});

export interface CardFooterProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardFooterVariants> {}

const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardFooterVariants({ padding, className }))}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";

/* ─────────────────────────────────────────────────────────────────────────────
   Motion Card (Animated)
   ───────────────────────────────────────────────────────────────────────────── */

interface MotionCardProps extends HTMLMotionProps<"div"> {
  variant?: VariantProps<typeof cardVariants>["variant"];
  padding?: VariantProps<typeof cardVariants>["padding"];
}

const MotionCard = React.forwardRef<HTMLDivElement, MotionCardProps>(
  ({ className, variant, padding, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={cn(cardVariants({ variant, padding, className }))}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
        {...props}
      />
    );
  },
);
MotionCard.displayName = "MotionCard";

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  MotionCard,
  cardVariants,
};

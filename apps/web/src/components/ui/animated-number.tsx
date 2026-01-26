"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { springs, durations } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * ANIMATED NUMBER - Rolling digit animation for metrics
 * ═══════════════════════════════════════════════════════════════════
 */

export type NumberFormat = "number" | "currency" | "percentage" | "compact";

interface AnimatedNumberProps {
  /** The numeric value to display */
  value: number;
  /** How to format the number */
  format?: NumberFormat;
  /** Locale for formatting (default: en-US) */
  locale?: string;
  /** Animation duration in ms */
  duration?: number;
  /** Additional className */
  className?: string;
  /** Prefix to display before the number */
  prefix?: string;
  /** Suffix to display after the number */
  suffix?: string;
  /** Number of decimal places (for number/currency) */
  decimals?: number;
  /** Currency code for currency format */
  currency?: string;
}

// Format number based on type
function formatNumber(
  value: number,
  format: NumberFormat,
  locale: string,
  decimals?: number,
  currency?: string
): string {
  switch (format) {
    case "currency":
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency: currency || "USD",
        minimumFractionDigits: decimals ?? 0,
        maximumFractionDigits: decimals ?? 0,
      }).format(value);

    case "percentage":
      return new Intl.NumberFormat(locale, {
        style: "percent",
        minimumFractionDigits: decimals ?? 1,
        maximumFractionDigits: decimals ?? 1,
      }).format(value / 100);

    case "compact":
      return new Intl.NumberFormat(locale, {
        notation: "compact",
        compactDisplay: "short",
        maximumFractionDigits: 1,
      }).format(value);

    case "number":
    default:
      return new Intl.NumberFormat(locale, {
        minimumFractionDigits: decimals ?? 0,
        maximumFractionDigits: decimals ?? 0,
      }).format(value);
  }
}

// Split formatted number into individual characters
function splitNumber(formatted: string): string[] {
  return formatted.split("");
}

// Single digit component with rolling animation
function AnimatedDigit({
  digit,
  index,
  total,
}: {
  digit: string;
  index: number;
  total: number;
}) {
  const isNumber = /\d/.test(digit);
  const prefersReducedMotion = useReducedMotion();

  // Calculate stagger delay based on position (right to left)
  const delay = (total - index - 1) * 0.03;

  if (!isNumber || prefersReducedMotion) {
    // Non-numeric characters or reduced motion - just fade
    return (
      <motion.span
        key={`${index}-${digit}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: durations.fast }}
        className="inline-block"
      >
        {digit}
      </motion.span>
    );
  }

  // Numeric digits get the rolling animation
  return (
    <motion.span
      key={`${index}-${digit}`}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 20, opacity: 0 }}
      transition={{
        ...springs.snappy,
        delay,
      }}
      className="inline-block"
    >
      {digit}
    </motion.span>
  );
}

export function AnimatedNumber({
  value,
  format = "number",
  locale = "en-US",
  duration = 500,
  className,
  prefix,
  suffix,
  decimals,
  currency = "USD",
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(value);
  const [isAnimating, setIsAnimating] = useState(false);
  const prevValueRef = useRef(value);
  const prefersReducedMotion = useReducedMotion();

  // Update display value when input value changes
  useEffect(() => {
    if (value !== prevValueRef.current) {
      setIsAnimating(true);
      prevValueRef.current = value;

      if (prefersReducedMotion) {
        // Instant update for reduced motion
        setDisplayValue(value);
        setIsAnimating(false);
      } else {
        // Animate the transition
        const startTime = Date.now();
        const startValue = displayValue;
        const diff = value - startValue;

        const animate = () => {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);

          // Ease out quad
          const eased = 1 - (1 - progress) * (1 - progress);
          const current = startValue + diff * eased;

          setDisplayValue(current);

          if (progress < 1) {
            requestAnimationFrame(animate);
          } else {
            setDisplayValue(value);
            setIsAnimating(false);
          }
        };

        requestAnimationFrame(animate);
      }
    }
  }, [value, duration, prefersReducedMotion]);

  // Format the display value
  const formatted = useMemo(
    () => formatNumber(displayValue, format, locale, decimals, currency),
    [displayValue, format, locale, decimals, currency]
  );

  // Split into characters
  const characters = useMemo(() => splitNumber(formatted), [formatted]);

  return (
    <span
      className={cn(
        "inline-flex items-baseline font-mono tabular-nums",
        className
      )}
    >
      {prefix && <span className="mr-0.5">{prefix}</span>}

      <span className="inline-flex overflow-hidden">
        <AnimatePresence mode="popLayout" initial={false}>
          {characters.map((char, index) => (
            <AnimatedDigit
              key={`${index}-${char}-${isAnimating}`}
              digit={char}
              index={index}
              total={characters.length}
            />
          ))}
        </AnimatePresence>
      </span>

      {suffix && <span className="ml-0.5">{suffix}</span>}
    </span>
  );
}

/**
 * Simple counter that animates from 0 to target value
 */
interface CountUpProps {
  /** Target value */
  end: number;
  /** Starting value (default: 0) */
  start?: number;
  /** Animation duration in ms */
  duration?: number;
  /** Decimal places */
  decimals?: number;
  /** Additional className */
  className?: string;
  /** Prefix */
  prefix?: string;
  /** Suffix */
  suffix?: string;
}

export function CountUp({
  end,
  start = 0,
  duration = 1000,
  decimals = 0,
  className,
  prefix,
  suffix,
}: CountUpProps) {
  const [count, setCount] = useState(start);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (prefersReducedMotion) {
      setCount(end);
      return;
    }

    const startTime = Date.now();
    const diff = end - start;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Ease out expo
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = start + diff * eased;

      setCount(current);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setCount(end);
      }
    };

    requestAnimationFrame(animate);
  }, [end, start, duration, prefersReducedMotion]);

  const formatted = count.toFixed(decimals);

  return (
    <span className={cn("font-mono tabular-nums", className)}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}

export default AnimatedNumber;

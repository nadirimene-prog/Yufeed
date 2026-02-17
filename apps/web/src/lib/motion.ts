/**
 * ═══════════════════════════════════════════════════════════════════
 * YUFEED SENTINEL - Motion Configuration
 * Framer Motion variants and utilities for consistent animations
 * ═══════════════════════════════════════════════════════════════════
 */

import { Variants, Transition, TargetAndTransition } from "framer-motion";
import { useState, useEffect } from "react";

/* ══════════════════════════════════════════════════════════════════
   SPRING CONFIGURATIONS
   ══════════════════════════════════════════════════════════════════ */

export const springs = {
  /** Gentle, smooth animations for subtle movements */
  gentle: {
    type: "spring" as const,
    stiffness: 200,
    damping: 30,
  },
  /** Snappy, responsive animations for interactions */
  snappy: {
    type: "spring" as const,
    stiffness: 400,
    damping: 30,
  },
  /** Bouncy animations for playful elements */
  bouncy: {
    type: "spring" as const,
    stiffness: 300,
    damping: 15,
  },
  /** Very soft for background elements */
  soft: {
    type: "spring" as const,
    stiffness: 100,
    damping: 20,
  },
  /** Quick response for micro-interactions */
  quick: {
    type: "spring" as const,
    stiffness: 500,
    damping: 35,
  },
} as const;

/* ══════════════════════════════════════════════════════════════════
   EASING CURVES
   ══════════════════════════════════════════════════════════════════ */

export const easings = {
  /** Standard ease out - decelerating */
  out: [0, 0, 0.2, 1] as const,
  /** Standard ease in - accelerating */
  in: [0.4, 0, 1, 1] as const,
  /** Standard ease in-out */
  inOut: [0.4, 0, 0.2, 1] as const,
  /** Exponential ease out - dramatic deceleration */
  outExpo: [0.16, 1, 0.3, 1] as const,
  /** Quart ease out - smooth deceleration */
  outQuart: [0.25, 1, 0.5, 1] as const,
  /** Spring-like easing for CSS */
  spring: [0.34, 1.56, 0.64, 1] as const,
  /** Bouncy easing */
  bounce: [0.68, -0.6, 0.32, 1.6] as const,
} as const;

/* ══════════════════════════════════════════════════════════════════
   DURATION CONSTANTS
   ══════════════════════════════════════════════════════════════════ */

export const durations = {
  instant: 0.075,
  faster: 0.1,
  fast: 0.15,
  normal: 0.25,
  slow: 0.35,
  slower: 0.5,
  dramatic: 0.7,
} as const;

/* ══════════════════════════════════════════════════════════════════
   TRANSITION PRESETS
   ══════════════════════════════════════════════════════════════════ */

export const transitions = {
  /** Fast, snappy transition for micro-interactions */
  fast: {
    duration: durations.fast,
    ease: easings.out,
  } as Transition,

  /** Standard transition for most animations */
  default: {
    duration: durations.normal,
    ease: easings.outExpo,
  } as Transition,

  /** Slow, dramatic transition for page-level animations */
  slow: {
    duration: durations.slow,
    ease: easings.outExpo,
  } as Transition,

  /** Spring transition for organic feel */
  spring: springs.snappy as Transition,

  /** Gentle spring for subtle movements */
  gentleSpring: springs.gentle as Transition,

  /** Bouncy spring for playful elements */
  bouncySpring: springs.bouncy as Transition,
} as const;

/* ══════════════════════════════════════════════════════════════════
   ANIMATION VARIANTS
   ══════════════════════════════════════════════════════════════════ */

/** Fade in animation */
export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: transitions.default,
  },
  exit: {
    opacity: 0,
    transition: transitions.fast,
  },
};

/** Fade in with upward movement */
export const fadeInUp: Variants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: transitions.default,
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: transitions.fast,
  },
};

/** Fade in with blur effect - premium reveal */
export const fadeInBlur: Variants = {
  initial: {
    opacity: 0,
    y: 20,
    filter: "blur(10px)",
  },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      duration: durations.slow,
      ease: easings.outExpo,
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    filter: "blur(5px)",
    transition: transitions.fast,
  },
};

/** Scale in animation */
export const scaleIn: Variants = {
  initial: {
    opacity: 0,
    scale: 0.95,
  },
  animate: {
    opacity: 1,
    scale: 1,
    transition: transitions.spring,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: transitions.fast,
  },
};

/** Slide in from left */
export const slideInLeft: Variants = {
  initial: {
    opacity: 0,
    x: -20,
  },
  animate: {
    opacity: 1,
    x: 0,
    transition: transitions.default,
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: transitions.fast,
  },
};

/** Slide in from right */
export const slideInRight: Variants = {
  initial: {
    opacity: 0,
    x: 20,
  },
  animate: {
    opacity: 1,
    x: 0,
    transition: transitions.default,
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: transitions.fast,
  },
};

/* ══════════════════════════════════════════════════════════════════
   PAGE TRANSITION VARIANTS
   ══════════════════════════════════════════════════════════════════ */

export const pageTransition: Variants = {
  initial: {
    opacity: 0,
    y: 20,
    filter: "blur(10px)",
  },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      duration: durations.slow,
      ease: easings.outExpo,
      staggerChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    filter: "blur(5px)",
    transition: {
      duration: durations.fast,
    },
  },
};

/* ══════════════════════════════════════════════════════════════════
   STAGGER VARIANTS
   ══════════════════════════════════════════════════════════════════ */

/** Container for staggered children */
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1,
    },
  },
};

/** Container with slower stagger */
export const staggerContainerSlow: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.15,
    },
  },
};

/** Individual stagger item */
export const staggerItem: Variants = {
  initial: {
    opacity: 0,
    y: 15,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: transitions.default,
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: transitions.fast,
  },
};

/** Stagger item with scale */
export const staggerItemScale: Variants = {
  initial: {
    opacity: 0,
    y: 15,
    scale: 0.95,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: transitions.spring,
  },
};

/* ══════════════════════════════════════════════════════════════════
   COMPONENT-SPECIFIC VARIANTS
   ══════════════════════════════════════════════════════════════════ */

/** Card hover effect - lift and glow */
export const cardHover: Variants = {
  initial: {
    y: 0,
    boxShadow: "0 8px 32px rgba(0, 0, 0, 0.12)",
  },
  hover: {
    y: -4,
    boxShadow:
      "0 16px 48px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(109, 90, 205, 0.1)",
    transition: springs.snappy,
  },
  tap: {
    y: -2,
    scale: 0.98,
    transition: springs.quick,
  },
};

/** Button press effect */
export const buttonPress: Variants = {
  initial: {
    scale: 1,
  },
  hover: {
    scale: 1.02,
    transition: springs.snappy,
  },
  tap: {
    scale: 0.98,
    transition: springs.quick,
  },
};

/** Sidebar item animation */
export const sidebarItem: Variants = {
  initial: {
    x: -10,
    opacity: 0,
  },
  animate: {
    x: 0,
    opacity: 1,
    transition: transitions.default,
  },
  hover: {
    x: 4,
    backgroundColor: "rgba(109, 90, 205, 0.1)",
    transition: springs.snappy,
  },
};

/** Modal/dialog animation */
export const modalAnimation: Variants = {
  initial: {
    opacity: 0,
    scale: 0.95,
    y: 10,
  },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      ...springs.snappy,
      opacity: { duration: durations.fast },
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: {
      duration: durations.fast,
    },
  },
};

/** Overlay/backdrop animation */
export const overlayAnimation: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { duration: durations.fast },
  },
  exit: {
    opacity: 0,
    transition: { duration: durations.fast },
  },
};

/** Tooltip animation */
export const tooltipAnimation: Variants = {
  initial: {
    opacity: 0,
    scale: 0.95,
    y: 5,
  },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springs.snappy,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: durations.faster },
  },
};

/** Dropdown animation */
export const dropdownAnimation: Variants = {
  initial: {
    opacity: 0,
    scale: 0.95,
    y: -5,
  },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springs.snappy,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -5,
    transition: { duration: durations.fast },
  },
};

/* ══════════════════════════════════════════════════════════════════
   GLOW/PULSE ANIMATIONS
   ══════════════════════════════════════════════════════════════════ */

/** Critical alert pulse - for attention */
export const criticalPulse: TargetAndTransition = {
  scale: [1, 1.02, 1],
  boxShadow: [
    "0 0 20px rgba(255, 51, 102, 0.4), 0 0 40px rgba(255, 51, 102, 0.2)",
    "0 0 30px rgba(255, 51, 102, 0.6), 0 0 60px rgba(255, 51, 102, 0.3)",
    "0 0 20px rgba(255, 51, 102, 0.4), 0 0 40px rgba(255, 51, 102, 0.2)",
  ],
  transition: {
    duration: 2,
    repeat: Infinity,
    ease: "easeInOut",
  },
};

/** Primary glow pulse */
export const primaryPulse: TargetAndTransition = {
  boxShadow: [
    "0 0 15px rgba(109, 90, 205, 0.3), 0 0 30px rgba(109, 90, 205, 0.1)",
    "0 0 25px rgba(109, 90, 205, 0.5), 0 0 50px rgba(109, 90, 205, 0.2)",
    "0 0 15px rgba(109, 90, 205, 0.3), 0 0 30px rgba(109, 90, 205, 0.1)",
  ],
  transition: {
    duration: 2,
    repeat: Infinity,
    ease: "easeInOut",
  },
};

/** Status indicator pulse */
export const statusPulse: TargetAndTransition = {
  scale: [1, 1.2, 1],
  opacity: [1, 0.7, 1],
  transition: {
    duration: 2,
    repeat: Infinity,
    ease: "easeInOut",
  },
};

/* ══════════════════════════════════════════════════════════════════
   NUMBER ANIMATION
   ══════════════════════════════════════════════════════════════════ */

/** Number roll animation for digits */
export const numberRoll: Variants = {
  initial: {
    y: "-100%",
    opacity: 0,
  },
  animate: {
    y: "0%",
    opacity: 1,
    transition: springs.snappy,
  },
  exit: {
    y: "100%",
    opacity: 0,
    transition: { duration: durations.fast },
  },
};

/* ══════════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS
   ══════════════════════════════════════════════════════════════════ */

/**
 * Calculate stagger delay for an item at a given index
 */
export function staggerDelay(index: number, baseDelay = 0.05): number {
  return index * baseDelay;
}

/**
 * Get transition config with custom delay
 */
export function withDelay(transition: Transition, delay: number): Transition {
  return {
    ...transition,
    delay,
  };
}

/**
 * Create a custom stagger container with specific timing
 */
export function createStaggerContainer(
  staggerChildren = 0.05,
  delayChildren = 0.1,
): Variants {
  return {
    initial: {},
    animate: {
      transition: {
        staggerChildren,
        delayChildren,
      },
    },
  };
}

/**
 * Check if user prefers reduced motion
 * Use this to conditionally apply animations
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Get animation variants based on reduced motion preference
 * Returns static values if user prefers reduced motion
 */
export function getReducedMotionVariants(
  variants: Variants,
  reducedVariants?: Variants,
): Variants {
  if (prefersReducedMotion()) {
    return (
      reducedVariants ?? {
        initial: { opacity: 1 },
        animate: { opacity: 1 },
        exit: { opacity: 1 },
      }
    );
  }
  return variants;
}

/* ══════════════════════════════════════════════════════════════════
   REDUCED MOTION VARIANTS
   Static alternatives for accessibility
   ══════════════════════════════════════════════════════════════════ */

/** Static fade - no animation */
export const reducedFadeIn: Variants = {
  initial: { opacity: 1 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

/** Static page transition */
export const reducedPageTransition: Variants = {
  initial: { opacity: 1 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

/** Static stagger container - immediate children */
export const reducedStaggerContainer: Variants = {
  initial: {},
  animate: {},
  exit: {},
};

/** Static stagger item */
export const reducedStaggerItem: Variants = {
  initial: { opacity: 1 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

/** Static card hover - no lift, just color change */
export const reducedCardHover: Variants = {
  initial: {},
  hover: {
    boxShadow: "0 0 0 1px rgba(109, 90, 205, 0.2)",
  },
  tap: {},
};

/** Static modal - instant appear */
export const reducedModalAnimation: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

/**
 * Get motion-safe animation props
 * Returns reduced variants when user prefers reduced motion
 */
export function getMotionSafeVariants<T extends Variants>(
  fullVariants: T,
  reducedVariants?: Variants,
): Variants {
  if (typeof window === "undefined") return fullVariants;

  if (prefersReducedMotion()) {
    return reducedVariants ?? reducedFadeIn;
  }
  return fullVariants;
}

/**
 * Get motion-safe transition
 * Returns instant transition when user prefers reduced motion
 */
export function getMotionSafeTransition(
  fullTransition: Transition,
): Transition {
  if (typeof window === "undefined") return fullTransition;

  if (prefersReducedMotion()) {
    return { duration: 0 };
  }
  return fullTransition;
}

/* ══════════════════════════════════════════════════════════════════
   ANIMATION PRESETS FOR COMMON USE CASES
   ══════════════════════════════════════════════════════════════════ */

export const animationPresets = {
  /** For page content */
  pageContent: {
    variants: pageTransition,
    initial: "initial",
    animate: "animate",
    exit: "exit",
  },

  /** For lists of items */
  staggeredList: {
    container: staggerContainer,
    item: staggerItem,
  },

  /** For cards */
  card: {
    variants: cardHover,
    initial: "initial",
    whileHover: "hover",
    whileTap: "tap",
  },

  /** For buttons */
  button: {
    variants: buttonPress,
    initial: "initial",
    whileHover: "hover",
    whileTap: "tap",
  },

  /** For modals */
  modal: {
    variants: modalAnimation,
    initial: "initial",
    animate: "animate",
    exit: "exit",
  },

  /** For tooltips */
  tooltip: {
    variants: tooltipAnimation,
    initial: "initial",
    animate: "animate",
    exit: "exit",
  },
} as const;

/* ══════════════════════════════════════════════════════════════════
   MOTION-SAFE PRESETS
   Use these when you need accessibility-aware animations
   ══════════════════════════════════════════════════════════════════ */

export const motionSafePresets = {
  /** Page content with reduced motion fallback */
  pageContent: () => ({
    variants: prefersReducedMotion() ? reducedPageTransition : pageTransition,
    initial: "initial",
    animate: "animate",
    exit: "exit",
  }),

  /** Staggered list with reduced motion fallback */
  staggeredList: () => ({
    container: prefersReducedMotion()
      ? reducedStaggerContainer
      : staggerContainer,
    item: prefersReducedMotion() ? reducedStaggerItem : staggerItem,
  }),

  /** Card with reduced motion fallback */
  card: () => ({
    variants: prefersReducedMotion() ? reducedCardHover : cardHover,
    initial: "initial",
    whileHover: "hover",
    whileTap: "tap",
  }),

  /** Modal with reduced motion fallback */
  modal: () => ({
    variants: prefersReducedMotion() ? reducedModalAnimation : modalAnimation,
    initial: "initial",
    animate: "animate",
    exit: "exit",
  }),
} as const;

/* ══════════════════════════════════════════════════════════════════
   REACT HOOKS FOR MOTION PREFERENCES
   ══════════════════════════════════════════════════════════════════ */

/**
 * React hook to detect reduced motion preference
 * Updates when user changes system preference
 *
 * @example
 * const prefersReduced = useReducedMotion();
 * return (
 *   <motion.div
 *     animate={prefersReduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
 *     initial={prefersReduced ? { opacity: 1 } : { opacity: 0, y: 20 }}
 *   />
 * );
 */
export function useReducedMotion(): boolean {
  const [prefersReduced, setPrefersReduced] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    // Check initial preference
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = (matches: boolean) => {
      requestAnimationFrame(() => {
        setPrefersReduced(matches);
      });
    };
    updatePreference(mediaQuery.matches);

    // Listen for changes
    const handleChange = (event: MediaQueryListEvent) => {
      updatePreference(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleChange);
    } else {
      // Safari < 14 fallback
      mediaQuery.addListener(handleChange);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener("change", handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);

  return prefersReduced;
}

/**
 * Hook that returns appropriate variants based on motion preference
 *
 * @example
 * const variants = useMotionSafeVariants(fadeInBlur, reducedFadeIn);
 */
export function useMotionSafeVariants(
  fullVariants: Variants,
  reducedVariants: Variants = reducedFadeIn,
): Variants {
  const prefersReduced = useReducedMotion();
  return prefersReduced ? reducedVariants : fullVariants;
}

/**
 * Hook that returns appropriate transition based on motion preference
 */
export function useMotionSafeTransition(
  fullTransition: Transition,
): Transition {
  const prefersReduced = useReducedMotion();
  return prefersReduced ? { duration: 0 } : fullTransition;
}

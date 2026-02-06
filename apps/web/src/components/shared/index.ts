/**
 * Shared Components Index
 *
 * Centralized exports for all shared/reusable components.
 * This barrel export simplifies imports throughout the application.
 *
 * Usage:
 * ```tsx
 * import { StatusBadge, RiskLevelBar, LoadingBoundary } from '@/components/shared';
 * ```
 */

// Status components
export { StatusBadge } from './StatusBadge';

// Risk visualization components
export {
  RiskLevelBar,
  RiskLevelBadge,
  getRiskLevelFromScore,
  riskConfig,
} from './RiskLevelBar';

// Loading and state management components
export {
  LoadingBoundary,
  TableSkeleton,
  CardSkeleton,
} from './LoadingBoundary';

// Type exports
export type { default as StatusBadgeProps } from './StatusBadge';
export type { default as RiskLevelBarProps } from './RiskLevelBar';
export type { default as LoadingBoundaryProps } from './LoadingBoundary';

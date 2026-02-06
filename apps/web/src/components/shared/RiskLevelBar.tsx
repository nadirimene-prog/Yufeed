/**
 * RiskLevelBar Component
 *
 * A reusable component for visualizing risk levels across the application.
 * Replaces 8+ inline risk level implementations with a single, consistent component.
 *
 * Features:
 * - Color-coded risk levels (low, medium, high, critical)
 * - Optional numeric risk score display
 * - Smooth transitions and animations
 * - Accessible with proper ARIA attributes
 * - Responsive sizing
 *
 * Usage:
 * ```tsx
 * <RiskLevelBar level="low" />
 * <RiskLevelBar level="high" score={85.5} />
 * <RiskLevelBar level="critical" score={95} showLabel={false} />
 * <RiskLevelBar level="medium" size="sm" />
 * ```
 */

import { cn } from '@/lib/utils';

interface RiskLevelBarProps {
  level: 'low' | 'medium' | 'high' | 'critical';
  score?: number;
  showLabel?: boolean;
  showScore?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

interface RiskConfig {
  color: string;
  bgColor: string;
  width: string;
  label: string;
  minScore: number;
  maxScore: number;
}

const riskConfig: Record<string, RiskConfig> = {
  low: {
    color: 'bg-green-500 dark:bg-green-600',
    bgColor: 'bg-green-100 dark:bg-green-950',
    width: '25%',
    label: 'Low Risk',
    minScore: 0,
    maxScore: 25,
  },
  medium: {
    color: 'bg-yellow-500 dark:bg-yellow-600',
    bgColor: 'bg-yellow-100 dark:bg-yellow-950',
    width: '50%',
    label: 'Medium Risk',
    minScore: 25,
    maxScore: 60,
  },
  high: {
    color: 'bg-orange-500 dark:bg-orange-600',
    bgColor: 'bg-orange-100 dark:bg-orange-950',
    width: '75%',
    label: 'High Risk',
    minScore: 60,
    maxScore: 85,
  },
  critical: {
    color: 'bg-red-500 dark:bg-red-600',
    bgColor: 'bg-red-100 dark:bg-red-950',
    width: '100%',
    label: 'Critical Risk',
    minScore: 85,
    maxScore: 100,
  },
};

/**
 * Determine risk level from numeric score
 */
export function getRiskLevelFromScore(score: number): 'low' | 'medium' | 'high' | 'critical' {
  if (score >= 85) return 'critical';
  if (score >= 60) return 'high';
  if (score >= 25) return 'medium';
  return 'low';
}

export function RiskLevelBar({
  level,
  score,
  showLabel = true,
  showScore = true,
  size = 'md',
  className,
}: RiskLevelBarProps) {
  const config = riskConfig[level];

  // Calculate width based on score if provided, otherwise use config default
  const calculatedWidth = score !== undefined
    ? `${Math.min(Math.max(score, 0), 100)}%`
    : config.width;

  // Size classes
  const heightClass = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  }[size];

  const textClass = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }[size];

  return (
    <div className={cn('w-full', className)} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score}>
      {showLabel && (
        <div className={cn('flex justify-between mb-1', textClass)}>
          <span className="font-medium">{config.label}</span>
          {showScore && score !== undefined && (
            <span className="font-semibold tabular-nums">{score.toFixed(1)}</span>
          )}
        </div>
      )}
      <div className={cn('w-full rounded-full overflow-hidden', config.bgColor, heightClass)}>
        <div
          className={cn(
            config.color,
            heightClass,
            'rounded-full transition-all duration-500 ease-out'
          )}
          style={{ width: calculatedWidth }}
          aria-label={`Risk level: ${config.label}${score !== undefined ? ` (${score.toFixed(1)})` : ''}`}
        />
      </div>
    </div>
  );
}

/**
 * RiskLevelBadge - Compact badge variant for tables and lists
 */
interface RiskLevelBadgeProps {
  level: 'low' | 'medium' | 'high' | 'critical';
  score?: number;
  className?: string;
}

export function RiskLevelBadge({ level, score, className }: RiskLevelBadgeProps) {
  const config = riskConfig[level];

  const badgeColorClass = {
    low: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  }[level];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        badgeColorClass,
        className
      )}
      role="status"
      aria-label={`Risk level: ${config.label}${score !== undefined ? ` (${score.toFixed(1)})` : ''}`}
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', config.color)}
        aria-hidden="true"
      />
      <span>{config.label}</span>
      {score !== undefined && (
        <span className="tabular-nums font-semibold">({score.toFixed(0)})</span>
      )}
    </span>
  );
}

/**
 * Export utilities for external use
 */
export { riskConfig };
export default RiskLevelBar;

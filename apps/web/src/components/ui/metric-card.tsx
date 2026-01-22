import { ReactNode } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sparkline } from './sparkline';
import { motion } from 'framer-motion';

export type MetricCardSize = 'sm' | 'md' | 'lg';
export type TrendDirection = 'up' | 'down' | 'neutral';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  trend?: {
    direction: TrendDirection;
    value: string;
    label?: string;
  };
  sparklineData?: { value: number }[];
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray';
  size?: MetricCardSize;
  className?: string;
  loading?: boolean;
}

const colorClasses = {
  blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400',
  green: 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400',
  yellow: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400',
  red: 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400',
  purple: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-purple-400',
  gray: 'text-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-400',
};

const sizeClasses = {
  sm: {
    container: 'p-4',
    title: 'text-xs',
    value: 'text-xl',
    icon: 'p-2 h-8 w-8',
    iconSize: 'h-4 w-4',
  },
  md: {
    container: 'p-6',
    title: 'text-sm',
    value: 'text-3xl',
    icon: 'p-3 h-12 w-12',
    iconSize: 'h-5 w-5',
  },
  lg: {
    container: 'p-8',
    title: 'text-base',
    value: 'text-4xl',
    icon: 'p-4 h-16 w-16',
    iconSize: 'h-6 w-6',
  },
};

export function MetricCard({
  title,
  value,
  icon,
  trend,
  sparklineData,
  color = 'gray',
  size = 'md',
  className,
  loading = false,
}: MetricCardProps) {
  const sizes = sizeClasses[size];

  if (loading) {
    return <MetricCardSkeleton size={size} className={className} />;
  }

  const TrendIcon = trend?.direction === 'up'
    ? TrendingUp
    : trend?.direction === 'down'
      ? TrendingDown
      : Minus;

  const trendColor = trend?.direction === 'up'
    ? 'text-green-600 dark:text-green-400'
    : trend?.direction === 'down'
      ? 'text-red-600 dark:text-red-400'
      : 'text-gray-500 dark:text-gray-400';

  const sparklineColor = trend?.direction === 'up' ? '#16a34a' : trend?.direction === 'down' ? '#dc2626' : '#6b7280';

  return (
    <motion.div
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      whileTap={{ scale: 0.98 }}
      className={cn(
        'bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden',
        sizes.container,
        className
      )}
    >
      <div className="flex items-start justify-between z-10 relative">
        <div className="flex-1">
          <p className={cn('text-gray-600 dark:text-gray-400 font-medium', sizes.title)}>
            {title}
          </p>
          <div className="flex items-end gap-2">
            <p className={cn('font-bold font-mono tracking-tight text-gray-900 dark:text-white mt-2', sizes.value)}>
              {value}
            </p>
            {sparklineData && (
              <div className="mb-1 ml-2">
                <Sparkline data={sparklineData} color={sparklineColor} width={80} height={30} />
              </div>
            )}
          </div>

          {trend && (
            <div className={cn('flex items-center gap-1 mt-2', trendColor)}>
              <TrendIcon className="h-4 w-4" />
              <span className="text-sm font-medium font-mono">{trend.value}</span>
              {trend.label && (
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
                  {trend.label}
                </span>
              )}
            </div>
          )}
        </div>

        {icon && (
          <div className={cn('rounded-lg', colorClasses[color], sizes.icon)}>
            <div className={sizes.iconSize}>{icon}</div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function MetricCardSkeleton({ size = 'md', className }: { size?: MetricCardSize; className?: string }) {
  const sizes = sizeClasses[size];

  return (
    <div
      className={cn(
        'bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm animate-pulse',
        sizes.container,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-24" />
          <div className="h-8 bg-gray-300 dark:bg-slate-600 rounded w-20" />
          <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-16" />
        </div>
        <div className={cn('rounded-lg bg-gray-200 dark:bg-slate-700', sizes.icon)} />
      </div>
    </div>
  );
}

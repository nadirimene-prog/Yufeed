import { cn } from '@/lib/utils';
import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'unknown';
export type BadgeSize = 'sm' | 'md' | 'lg';

interface RiskBadgeProps {
    level: RiskLevel;
    size?: BadgeSize;
    showIcon?: boolean;
    className?: string;
    animate?: boolean;
}

const riskConfig = {
    critical: {
        label: 'Critical',
        bgColor: 'bg-red-100 dark:bg-red-900/20',
        textColor: 'text-red-700 dark:text-red-400',
        borderColor: 'border-red-300 dark:border-red-800',
        Icon: XCircle,
    },
    high: {
        label: 'High',
        bgColor: 'bg-orange-100 dark:bg-orange-900/20',
        textColor: 'text-orange-700 dark:text-orange-400',
        borderColor: 'border-orange-300 dark:border-orange-800',
        Icon: AlertTriangle,
    },
    medium: {
        label: 'Medium',
        bgColor: 'bg-yellow-100 dark:bg-yellow-900/20',
        textColor: 'text-yellow-700 dark:text-yellow-400',
        borderColor: 'border-yellow-300 dark:border-yellow-800',
        Icon: Info,
    },
    low: {
        label: 'Low',
        bgColor: 'bg-green-100 dark:bg-green-900/20',
        textColor: 'text-green-700 dark:text-green-400',
        borderColor: 'border-green-300 dark:border-green-800',
        Icon: CheckCircle,
    },
    unknown: {
        label: 'Unknown',
        bgColor: 'bg-gray-100 dark:bg-gray-700',
        textColor: 'text-gray-700 dark:text-gray-400',
        borderColor: 'border-gray-300 dark:border-gray-600',
        Icon: Info,
    },
};

const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
};

const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
};

export function RiskBadge({
    level,
    size = 'md',
    showIcon = true,
    className,
    animate = false
}: RiskBadgeProps) {
    const config = riskConfig[level];
    const Icon = config.Icon;

    const shouldPulse = animate && (level === 'critical' || level === 'high');

    return (
        <span
            className={cn(
                'inline-flex items-center gap-1 font-medium rounded-full border',
                config.bgColor,
                config.textColor,
                config.borderColor,
                sizeClasses[size],
                shouldPulse && 'animate-pulse',
                className
            )}
            title={`Risk Level: ${config.label}`}
        >
            {showIcon && <Icon className={iconSizes[size]} />}
            <span>{config.label}</span>
        </span>
    );
}

// Numeric Risk Score Badge (0-100)
interface RiskScoreBadgeProps {
    score: number;
    size?: BadgeSize;
    showLabel?: boolean;
    className?: string;
}

export function RiskScoreBadge({
    score,
    size = 'md',
    showLabel = true,
    className
}: RiskScoreBadgeProps) {
    const level: RiskLevel =
        score >= 80 ? 'critical' :
            score >= 60 ? 'high' :
                score >= 40 ? 'medium' :
                    score >= 20 ? 'low' : 'unknown';

    const config = riskConfig[level];

    return (
        <div className={cn('inline-flex items-center gap-2', className)}>
            <span
                className={cn(
                    'inline-flex items-center justify-center font-bold rounded-full',
                    config.bgColor,
                    config.textColor,
                    size === 'sm' && 'h-8 w-8 text-sm',
                    size === 'md' && 'h-10 w-10 text-base',
                    size === 'lg' && 'h-12 w-12 text-lg'
                )}
            >
                {score}
            </span>
            {showLabel && (
                <RiskBadge level={level} size={size} showIcon={false} />
            )}
        </div>
    );
}

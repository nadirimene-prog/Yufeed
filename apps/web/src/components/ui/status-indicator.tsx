import { cn } from '@/lib/utils';
import { Circle } from 'lucide-react';

export type StatusState = 'active' | 'idle' | 'warning' | 'error' | 'success';
export type StatusSize = 'sm' | 'md' | 'lg';

interface StatusIndicatorProps {
    status: StatusState;
    label?: string;
    size?: StatusSize;
    pulse?: boolean;
    timestamp?: string;
    className?: string;
}

const statusConfig = {
    active: {
        color: 'bg-green-500',
        textColor: 'text-green-700 dark:text-green-400',
        label: 'Active',
    },
    idle: {
        color: 'bg-gray-400',
        textColor: 'text-gray-600 dark:text-gray-400',
        label: 'Idle',
    },
    warning: {
        color: 'bg-yellow-500',
        textColor: 'text-yellow-700 dark:text-yellow-400',
        label: 'Warning',
    },
    error: {
        color: 'bg-red-500',
        textColor: 'text-red-700 dark:text-red-400',
        label: 'Error',
    },
    success: {
        color: 'bg-green-500',
        textColor: 'text-green-700 dark:text-green-400',
        label: 'Success',
    },
};

const sizeConfig = {
    sm: {
        dot: 'h-2 w-2',
        text: 'text-xs',
    },
    md: {
        dot: 'h-2.5 w-2.5',
        text: 'text-sm',
    },
    lg: {
        dot: 'h-3 w-3',
        text: 'text-base',
    },
};

export function StatusIndicator({
    status,
    label,
    size = 'md',
    pulse = false,
    timestamp,
    className,
}: StatusIndicatorProps) {
    const config = statusConfig[status];
    const sizes = sizeConfig[size];
    const displayLabel = label || config.label;

    return (
        <div className={cn('inline-flex items-center gap-2', className)}>
            <div className="relative">
                <Circle
                    className={cn(
                        'rounded-full',
                        config.color,
                        sizes.dot,
                        'fill-current'
                    )}
                />
                {pulse && (
                    <span
                        className={cn(
                            'absolute inset-0 rounded-full animate-ping',
                            config.color,
                            'opacity-75'
                        )}
                    />
                )}
            </div>

            <div className="flex flex-col">
                <span className={cn('font-medium', config.textColor, sizes.text)}>
                    {displayLabel}
                </span>
                {timestamp && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                        {timestamp}
                    </span>
                )}
            </div>
        </div>
    );
}

// Simple dot-only version
interface StatusDotProps {
    status: StatusState;
    size?: StatusSize;
    pulse?: boolean;
    className?: string;
}

export function StatusDot({ status, size = 'md', pulse = false, className }: StatusDotProps) {
    const config = statusConfig[status];
    const sizes = sizeConfig[size];

    return (
        <div className={cn('relative inline-flex', className)}>
            <Circle
                className={cn(
                    'rounded-full',
                    config.color,
                    sizes.dot,
                    'fill-current'
                )}
            />
            {pulse && (
                <span
                    className={cn(
                        'absolute inset-0 rounded-full animate-ping',
                        config.color,
                        'opacity-75'
                    )}
                />
            )}
        </div>
    );
}

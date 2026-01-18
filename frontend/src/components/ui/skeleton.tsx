import { cn } from '@/lib/utils';
import { CSSProperties } from 'react';

interface SkeletonProps {
    className?: string;
    style?: CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
    return (
        <div
            className={cn(
                'animate-pulse rounded-md bg-gray-200 dark:bg-slate-700',
                className
            )}
            style={style}
        />
    );
}

// Preset skeleton layouts
export function CardSkeleton() {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 p-6 space-y-4">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-8 w-48" />
            <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
            </div>
        </div>
    );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
    return (
        <div className="space-y-3">
            {Array.from({ length: rows }).map((_, i) => (
                <div key={i} className="flex gap-4 items-center">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-1/3" />
                        <Skeleton className="h-3 w-1/2" />
                    </div>
                    <Skeleton className="h-8 w-20" />
                </div>
            ))}
        </div>
    );
}

export function GraphSkeleton() {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 p-6">
            <Skeleton className="h-6 w-48 mb-6" />
            <div className="h-64 flex items-end justify-between gap-2">
                {Array.from({ length: 12 }).map((_, i) => (
                    <Skeleton
                        key={i}
                        className="flex-1"
                        style={{ height: `${Math.random() * 100}%` }}
                    />
                ))}
            </div>
            <div className="flex justify-between mt-4">
                {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-3 w-12" />
                ))}
            </div>
        </div>
    );
}

export function TextSkeleton({ lines = 3 }: { lines?: number }) {
    return (
        <div className="space-y-2">
            {Array.from({ length: lines }).map((_, i) => (
                <Skeleton
                    key={i}
                    className={cn(
                        'h-4',
                        i === lines - 1 ? 'w-2/3' : 'w-full'
                    )}
                />
            ))}
        </div>
    );
}

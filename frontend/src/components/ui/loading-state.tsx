import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  type?: 'fullscreen' | 'inline' | 'spinner';
  className?: string;
}

export function LoadingState({
  message = 'Loading...',
  type = 'inline',
  className = '',
}: LoadingStateProps) {
  if (type === 'fullscreen') {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-gray-700 dark:text-gray-300">{message}</p>
        </div>
      </div>
    );
  }

  if (type === 'spinner') {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    );
  }

  // Inline type
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
      <span className="text-gray-600 dark:text-gray-400">{message}</span>
    </div>
  );
}

// Skeleton loading components
export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex space-x-4 animate-pulse">
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="border rounded-lg p-6 space-y-4 animate-pulse">
      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
    </div>
  );
}

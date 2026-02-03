import { Maximize2, ZoomIn, ZoomOut, Locate, Play, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';

interface GraphControlsProps {
    onZoomIn?: () => void;
    onZoomOut?: () => void;
    onResetZoom?: () => void;
    onCenter?: () => void;
    onTogglePhysics?: () => void;
    isPhysicsRunning?: boolean;
    className?: string;
}

export function GraphControls({
    onZoomIn,
    onZoomOut,
    onResetZoom,
    onCenter,
    onTogglePhysics,
    isPhysicsRunning = true,
    className,
}: GraphControlsProps) {
    return (
        <div className={cn('flex flex-col gap-2 bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 p-2 shadow-lg', className)}>
            {/* Zoom Controls */}
            <div className="flex flex-col gap-1">
                <button
                    onClick={onZoomIn}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors group"
                    title="Zoom In"
                >
                    <ZoomIn className="h-5 w-5 text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white" />
                </button>

                <button
                    onClick={onZoomOut}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors group"
                    title="Zoom Out"
                >
                    <ZoomOut className="h-5 w-5 text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white" />
                </button>

                <button
                    onClick={onResetZoom}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors group"
                    title="Reset Zoom"
                >
                    <Maximize2 className="h-5 w-5 text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white" />
                </button>
            </div>

            <div className="h-px bg-gray-200 dark:bg-slate-700" />

            {/* Other Controls */}
            <div className="flex flex-col gap-1">
                <button
                    onClick={onCenter}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors group"
                    title="Center Graph"
                >
                    <Locate className="h-5 w-5 text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white" />
                </button>

                <button
                    onClick={onTogglePhysics}
                    className={cn(
                        'p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors group',
                        isPhysicsRunning && 'bg-blue-50 dark:bg-blue-900/20'
                    )}
                    title={isPhysicsRunning ? 'Pause Physics' : 'Resume Physics'}
                >
                    {isPhysicsRunning ? (
                        <Pause className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    ) : (
                        <Play className="h-5 w-5 text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-white" />
                    )}
                </button>
            </div>
        </div>
    );
}

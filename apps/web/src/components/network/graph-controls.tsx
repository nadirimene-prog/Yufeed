import { Maximize2, ZoomIn, ZoomOut, Locate, Play, Pause } from "lucide-react";
import { cn } from "@/lib/utils";

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
    <div
      className={cn(
        "flex flex-col gap-2 bg-white  rounded-lg border border-slate-200  p-2 shadow-lg",
        className,
      )}
    >
      {/* Zoom Controls */}
      <div className="flex flex-col gap-1">
        <button
          onClick={onZoomIn}
          className="p-2 hover:bg-slate-100  rounded-md transition-colors group"
          title="Zoom In"
        >
          <ZoomIn className="h-5 w-5 text-slate-600  group-hover:text-slate-900 " />
        </button>

        <button
          onClick={onZoomOut}
          className="p-2 hover:bg-slate-100  rounded-md transition-colors group"
          title="Zoom Out"
        >
          <ZoomOut className="h-5 w-5 text-slate-600  group-hover:text-slate-900 " />
        </button>

        <button
          onClick={onResetZoom}
          className="p-2 hover:bg-slate-100  rounded-md transition-colors group"
          title="Reset Zoom"
        >
          <Maximize2 className="h-5 w-5 text-slate-600  group-hover:text-slate-900 " />
        </button>
      </div>

      <div className="h-px bg-slate-200 " />

      {/* Other Controls */}
      <div className="flex flex-col gap-1">
        <button
          onClick={onCenter}
          className="p-2 hover:bg-slate-100  rounded-md transition-colors group"
          title="Center Graph"
        >
          <Locate className="h-5 w-5 text-slate-600  group-hover:text-slate-900 " />
        </button>

        <button
          onClick={onTogglePhysics}
          className={cn(
            "p-2 hover:bg-slate-100  rounded-md transition-colors group",
            isPhysicsRunning && "bg-blue-50 ",
          )}
          title={isPhysicsRunning ? "Pause Physics" : "Resume Physics"}
        >
          {isPhysicsRunning ? (
            <Pause className="h-5 w-5 text-blue-600 " />
          ) : (
            <Play className="h-5 w-5 text-slate-600  group-hover:text-slate-900 " />
          )}
        </button>
      </div>
    </div>
  );
}

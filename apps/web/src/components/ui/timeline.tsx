import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Circle, CheckCircle, AlertCircle, Info, Clock } from "lucide-react";

export type TimelineEventType =
  | "success"
  | "warning"
  | "error"
  | "info"
  | "neutral";

export interface TimelineEvent {
  id: string | number;
  title: string;
  description?: string;
  timestamp: string | Date;
  type?: TimelineEventType;
  icon?: ReactNode;
  metadata?: Record<string, unknown>;
  actor?: string;
}

interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
  compact?: boolean;
}

const typeConfig = {
  success: {
    color: "text-risk-low",
    bgColor: "bg-risk-low-soft",
    borderColor: "border-risk-low/20",
    icon: CheckCircle,
  },
  warning: {
    color: "text-risk-medium",
    bgColor: "bg-risk-medium-soft",
    borderColor: "border-risk-medium/20",
    icon: AlertCircle,
  },
  error: {
    color: "text-risk-critical",
    bgColor: "bg-risk-critical-soft",
    borderColor: "border-risk-critical/20",
    icon: AlertCircle,
  },
  info: {
    color: "text-primary",
    bgColor: "bg-primary/10",
    borderColor: "border-primary/20",
    icon: Info,
  },
  neutral: {
    color: "text-foreground-secondary",
    bgColor: "bg-muted",
    borderColor: "border-border-subtle",
    icon: Circle,
  },
};

export function Timeline({
  events,
  className,
  compact = false,
}: TimelineProps) {
  const formatTimestamp = (timestamp: string | Date) => {
    const date =
      typeof timestamp === "string" ? new Date(timestamp) : timestamp;
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  };

  return (
    <div className={cn("space-y-1", className)}>
      {events.map((event, index) => {
        const config = typeConfig[event.type || "neutral"];
        const IconComponent = config.icon;
        const isLast = index === events.length - 1;

        return (
          <div key={event.id} className="relative flex gap-4">
            {/* Timeline Line and Icon */}
            <div className="flex flex-col items-center">
              {/* Icon Container */}
              <div
                className={cn(
                  "flex items-center justify-center rounded-full border-2 z-10",
                  compact ? "h-8 w-8" : "h-10 w-10",
                  config.bgColor,
                  config.borderColor,
                )}
              >
                {event.icon ? (
                  <div
                    className={cn(
                      compact ? "h-4 w-4" : "h-5 w-5",
                      config.color,
                    )}
                  >
                    {event.icon}
                  </div>
                ) : (
                  <IconComponent
                    className={cn(
                      compact ? "h-4 w-4" : "h-5 w-5",
                      config.color,
                    )}
                  />
                )}
              </div>

              {/* Connecting Line */}
              {!isLast && (
                <div
                  className={cn(
                    "w-0.5 flex-1 bg-border-subtle",
                    compact ? "my-1" : "my-2",
                  )}
                />
              )}
            </div>

            {/* Event Content */}
            <div className={cn("flex-1 pb-8", isLast && "pb-0")}>
              <div className="flex items-start justify-between gap-4 mb-1">
                <h4
                  className={cn(
                    "font-semibold text-foreground",
                    compact ? "text-sm" : "text-base",
                  )}
                >
                  {event.title}
                </h4>
                <time
                  className={cn(
                    "flex items-center gap-1 whitespace-nowrap text-foreground-tertiary",
                    compact ? "text-xs" : "text-sm",
                  )}
                >
                  <Clock className="h-3 w-3" />
                  {formatTimestamp(event.timestamp)}
                </time>
              </div>

              {event.description && (
                <p
                  className={cn(
                    "text-foreground-secondary",
                    compact ? "text-xs" : "text-sm",
                  )}
                >
                  {event.description}
                </p>
              )}

              {event.actor && (
                <p className="mt-1 text-xs text-foreground-tertiary">
                  by {event.actor}
                </p>
              )}

              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.entries(event.metadata).map(([key, value]) => (
                    <span
                      key={key}
                      className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs text-foreground-secondary"
                    >
                      <span className="font-medium mr-1">{key}:</span>
                      {String(value)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Compact variant for sidebar or small spaces
export function TimelineCompact({
  events,
  className,
}: Omit<TimelineProps, "compact">) {
  return <Timeline events={events} className={className} compact />;
}

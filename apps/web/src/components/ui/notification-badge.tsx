import { cn } from "@/lib/utils";

interface NotificationBadgeProps {
  count?: number;
  max?: number;
  dot?: boolean;
  pulse?: boolean;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function NotificationBadge({
  count = 0,
  max = 99,
  dot = false,
  pulse = false,
  size = "md",
  className,
}: NotificationBadgeProps) {
  if (!dot && count === 0) return null;

  const sizes = {
    sm: "h-4 w-4 text-[10px]",
    md: "h-5 w-5 text-xs",
    lg: "h-6 w-6 text-sm",
  };

  const dotSizes = {
    sm: "h-2 w-2",
    md: "h-2.5 w-2.5",
    lg: "h-3 w-3",
  };

  if (dot) {
    return (
      <span className="relative flex">
        <span
          className={cn(
            "absolute top-0 right-0 block rounded-full bg-red-600",
            dotSizes[size],
            pulse && "animate-ping",
            className,
          )}
        />
        <span
          className={cn(
            "relative inline-flex rounded-full bg-red-600",
            dotSizes[size],
            className,
          )}
        />
      </span>
    );
  }

  const displayCount = count > max ? `${max}+` : count;

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-red-600 font-semibold text-white",
        sizes[size],
        pulse && "animate-pulse",
        className,
      )}
    >
      {displayCount}
    </span>
  );
}

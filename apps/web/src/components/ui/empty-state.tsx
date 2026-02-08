import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { FileQuestion, Search, AlertTriangle, Inbox } from "lucide-react";

type EmptyStateVariant = "no-data" | "no-results" | "error" | "inbox";

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

const variantConfig = {
  "no-data": {
    icon: FileQuestion,
    title: "No data available",
    description: "There is no data to display at the moment.",
    iconColor: "text-gray-400 dark:text-gray-600",
  },
  "no-results": {
    icon: Search,
    title: "No results found",
    description: "Try adjusting your search or filter criteria.",
    iconColor: "text-blue-400 dark:text-blue-600",
  },
  error: {
    icon: AlertTriangle,
    title: "Something went wrong",
    description: "An error occurred while loading the data.",
    iconColor: "text-red-400 dark:text-red-600",
  },
  inbox: {
    icon: Inbox,
    title: "All caught up!",
    description: "No new items to review.",
    iconColor: "text-green-400 dark:text-green-600",
  },
};

export function EmptyState({
  variant = "no-data",
  title,
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  const config = variantConfig[variant];
  const Icon = icon || config.icon;
  const displayTitle = title || config.title;
  const displayDescription = description || config.description;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-12",
        className,
      )}
    >
      <div className={cn("mb-4", config.iconColor)}>
        {typeof Icon === "function" ? <Icon className="h-16 w-16" /> : Icon}
      </div>

      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        {displayTitle}
      </h3>

      <p className="text-gray-600 dark:text-gray-400 max-w-md mb-6">
        {displayDescription}
      </p>

      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Compact version for inline use
export function EmptyStateInline({ message }: { message: string }) {
  return (
    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
      {message}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { TimelineEvent, getDocumentTimeline } from "@/lib/compliance-api";
import { format } from "date-fns";
import {
  CheckCircle,
  Circle,
  FileText,
  Scale,
  History,
  FileClock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { logger } from "@/lib/logger";
import Link from "next/link";

interface TimelineViewProps {
  celex: string;
}

export function TimelineView({ celex }: TimelineViewProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        const data = await getDocumentTimeline(celex);
        // Sort by date descending (newest first)
        setEvents(
          data.sort(
            (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
          ),
        );
      } catch (error) {
        logger.error("Failed to load timeline", error);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [celex]);

  if (loading) {
    return (
      <div className="p-4 text-center text-slate-500 animate-pulse">
        Loading legislative history...
      </div>
    );
  }

  const getIcon = (type: TimelineEvent["type"]) => {
    switch (type) {
      case "ENTRY_INTO_FORCE":
        return CheckCircle;
      case "PUBLICATION":
        return FileText;
      case "PROPOSAL":
        return FileClock;
      case "AMENDMENT":
        return Scale;
      case "REPEAL":
        return History;
      default:
        return Circle;
    }
  };

  const getColor = (type: TimelineEvent["type"]) => {
    switch (type) {
      case "ENTRY_INTO_FORCE":
        return "text-green-600 bg-green-100   border-green-200 ";
      case "PUBLICATION":
        return "text-blue-600 bg-blue-100   border-blue-200 ";
      case "AMENDMENT":
        return "text-blue-600 bg-blue-100   border-blue-200 ";
      case "REPEAL":
        return "text-red-600 bg-red-100   border-red-200 ";
      default:
        return "text-slate-600 bg-slate-100   border-slate-200 ";
    }
  };

  return (
    <div className="bg-white  rounded-lg border border-slate-200  shadow-sm p-6">
      <h3 className="text-lg font-semibold text-slate-900  mb-6 flex items-center gap-2">
        <History className="h-5 w-5" />
        Legislative History
      </h3>

      <div className="relative pl-6 border-l-2 border-slate-200  space-y-8">
        {events.length === 0 && (
          <p className="text-sm text-slate-400  italic">
            No timeline events available for this document.
          </p>
        )}
        {events.map((event) => {
          const Icon = getIcon(event.type);
          const colorClass = getColor(event.type);

          return (
            <div key={event.id} className="relative group">
              {/* Dot on timeline */}
              <div
                className={cn(
                  "absolute -left-[31px] top-1 h-6 w-6 rounded-full border-2 flex items-center justify-center transition-transform group-hover:scale-110 bg-white ",
                  colorClass,
                )}
              >
                <Icon className="h-3 w-3" />
              </div>

              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={cn(
                        "text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wider",
                        colorClass,
                      )}
                    >
                      {event.type.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm text-slate-500  font-mono">
                      {format(new Date(event.date), "dd MMM yyyy")}
                    </span>
                  </div>
                  <h4 className="font-medium text-slate-900 ">{event.title}</h4>
                  {event.description && (
                    <p className="text-sm text-slate-600  mt-1 max-w-xl">
                      {event.description}
                    </p>
                  )}
                </div>

                {event.related_doc_celex && (
                  <Link
                    href={`/doc/${event.related_doc_celex}`}
                    className="shrink-0 text-xs font-medium text-blue-600 hover:text-blue-800   border border-blue-200  rounded px-2 py-1 hover:bg-blue-50  transition-colors"
                  >
                    View Doc &rarr;
                  </Link>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

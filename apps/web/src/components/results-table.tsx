"use client";

import Link from "next/link";
import { format } from "date-fns";
import { FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LegalDocument } from "@/lib/types";

interface ResultsTableProps {
  results: LegalDocument[];
  isLoading?: boolean;
}

export default function ResultsTable({
  results,
  isLoading,
}: ResultsTableProps) {
  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500">Loading results...</div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500">No documents found.</div>
    );
  }

  const getStatusColor = (status: LegalDocument["status"]) => {
    switch (status) {
      case "In Force":
        return "bg-green-100 text-green-800  ";
      case "No Longer in Force":
        return "bg-red-100 text-red-800  ";
      case "Proposal":
        return "bg-yellow-100 text-yellow-800  ";
      default:
        return "bg-slate-100 text-slate-800  ";
    }
  };

  const getTypeIcon = () => {
    // Icons could differ but using generic for now
    return <FileText className="h-4 w-4" />;
  };

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm  ">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600  ">
            <tr>
              <th className="px-6 py-4 font-semibold">CELEX</th>
              <th className="px-6 py-4 font-semibold w-1/2">Title</th>
              <th className="px-6 py-4 font-semibold">Date</th>
              <th className="px-6 py-4 font-semibold">Type</th>
              <th className="px-6 py-4 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 ">
            {results.map((doc) => (
              <tr
                key={doc.celex}
                className="group hover:bg-slate-50  transition-colors"
              >
                <td className="px-6 py-4 font-mono text-slate-500 ">
                  <Link
                    href={`/doc/${doc.celex}`}
                    className="font-medium text-blue-600 hover:text-blue-800  "
                  >
                    {doc.celex}
                  </Link>
                </td>
                <td className="px-6 py-4">
                  <Link href={`/doc/${doc.celex}`} className="block">
                    <p className="line-clamp-2 font-medium text-slate-900  group-hover:text-blue-600 ">
                      {doc.title}
                    </p>
                    {doc.topics.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {doc.topics.map((topic) => (
                          <span
                            key={topic}
                            className="inline-flex items-center rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600  "
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    )}
                  </Link>
                </td>
                <td className="px-6 py-4 text-slate-600  whitespace-nowrap">
                  {format(new Date(doc.date), "dd MMM yyyy")}
                </td>
                <td className="px-6 py-4 text-slate-600 ">
                  <div className="flex items-center gap-2">
                    {getTypeIcon()}
                    <span>{doc.type}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                      getStatusColor(doc.status),
                    )}
                  >
                    {doc.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

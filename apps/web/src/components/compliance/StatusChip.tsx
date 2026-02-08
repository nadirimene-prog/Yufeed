import React from "react";
import { ComplianceStatus } from "@/types/compliance";

interface StatusChipProps {
  status: ComplianceStatus | string;
}

const StatusChip: React.FC<StatusChipProps> = ({ status }) => {
  const getStyles = (s: string) => {
    switch (s.toLowerCase()) {
      case "approved":
        return "bg-blue-50 text-blue-700 border-blue-200"; // Sardine uses blue/clean look
      case "rejected":
        return "bg-gray-100 text-gray-600 border-gray-200 line-through decoration-gray-400";
      case "manual_review":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "pending":
        return "bg-yellow-50 text-yellow-700 border-yellow-200";
      default:
        return "bg-gray-50 text-gray-600";
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${getStyles(status)} capitalize`}
    >
      {status.replace("_", " ")}
    </span>
  );
};

export default StatusChip;

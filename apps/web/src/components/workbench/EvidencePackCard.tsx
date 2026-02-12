"use client";

import { motion } from "framer-motion";
import {
  Archive,
  Download,
  Hash,
  FileJson,
  FileText,
  FileArchive,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { staggerItem } from "@/lib/motion";
import type { EvidencePack } from "@/types/workbench";

interface EvidencePackCardProps {
  pack: EvidencePack;
  onClick?: () => void;
}

const formatIcons = {
  json: FileJson,
  pdf: FileText,
  zip: FileArchive,
} as const;

export function EvidencePackCard({ pack, onClick }: EvidencePackCardProps) {
  const FormatIcon =
    formatIcons[pack.format as keyof typeof formatIcons] ?? Archive;

  return (
    <motion.div
      variants={staggerItem}
      onClick={onClick}
      className={cn(
        "group rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 p-4",
        "transition-all duration-200 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600",
        onClick && "cursor-pointer",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-violet-50 dark:bg-violet-950/30">
          <FormatIcon className="h-5 w-5 text-violet-600 dark:text-violet-400" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
              {pack.pack_id}
            </h3>
            <span className="text-xs text-gray-400 dark:text-gray-500">
              v{pack.version}
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
            <span className="flex items-center gap-1">
              <Hash className="h-3 w-3" />
              {pack.integrity_hash.slice(0, 12)}…
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(pack.created_at).toLocaleDateString()}
            </span>
            <span className="uppercase font-medium">{pack.format}</span>
          </div>

          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Schema {pack.schema_version} · by {pack.created_by}
          </p>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            // Download would be handled externally
          }}
          className="p-2 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
        >
          <Download className="h-4 w-4 text-gray-400" />
        </button>
      </div>
    </motion.div>
  );
}

export default EvidencePackCard;

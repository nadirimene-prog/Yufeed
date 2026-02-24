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
        "group rounded-xl border border-slate-200 bg-white p-4",
        "transition-all duration-200 hover:shadow-md hover:border-slate-300",
        onClick && "cursor-pointer",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-[#0052FF]/5">
          <FormatIcon className="h-5 w-5 text-[#0052FF]" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-slate-900 truncate">
              {pack.pack_id}
            </h3>
            <span className="text-xs text-slate-400">v{pack.version}</span>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-400">
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

          <p className="text-xs text-slate-400 mt-1">
            Schema {pack.schema_version} · by {pack.created_by}
          </p>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            // Download would be handled externally
          }}
          className="p-2 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-slate-100 transition"
        >
          <Download className="h-4 w-4 text-slate-400" />
        </button>
      </div>
    </motion.div>
  );
}

export default EvidencePackCard;

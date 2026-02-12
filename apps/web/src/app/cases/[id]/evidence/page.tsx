"use client";

import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Plus, Archive, PackageOpen } from "lucide-react";
import {
  useEvidencePacks,
  useCreateEvidencePack,
} from "@/hooks/queries/useWorkbenchData";
import { EvidencePackCard } from "@/components/workbench/EvidencePackCard";
import { staggerContainer, fadeInBlur } from "@/lib/motion";

export default function CaseEvidencePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const caseId = params.id;

  const { data: packs = [], isLoading } = useEvidencePacks(caseId);
  const createMutation = useCreateEvidencePack(caseId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <motion.div
      variants={fadeInBlur}
      initial="initial"
      animate="animate"
      className="space-y-6"
    >
      {/* Header */}
      <div>
        <button
          onClick={() => router.push(`/cases/${caseId}`)}
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Case {caseId}
        </button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
              <Archive className="h-5 w-5 text-violet-500" />
              Evidence Packs
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Immutable evidence snapshots for this case.
            </p>
          </div>

          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="text-sm px-4 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50 transition flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" />
            {createMutation.isPending ? "Generating…" : "Generate Pack"}
          </button>
        </div>
      </div>

      {/* Evidence Packs */}
      {packs.length === 0 ? (
        <div className="text-center py-16">
          <PackageOpen className="h-12 w-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            No evidence packs yet
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Generate an evidence pack to create an immutable snapshot.
          </p>
        </div>
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="space-y-3"
        >
          {packs.map((pack) => (
            <EvidencePackCard key={pack.id} pack={pack} />
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

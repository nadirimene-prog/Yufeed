"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, FileText, Layers3 } from "lucide-react";
import { getPolicy, getPolicySections } from "@/lib/compliance-api";
import { handleApiError } from "@/lib/api-error-handler";
import type { Policy, PolicySection } from "@/types/compliance";
import { logger } from "@/lib/logger";

const policyStatusStyle = (status?: string | null) => {
  const value = (status ?? "draft").toLowerCase();
  if (value === "active") return "bg-emerald-50 text-emerald-700";
  if (value === "approved") return "bg-blue-50 text-blue-700";
  if (value === "in_review") return "bg-amber-50 text-amber-700";
  if (value === "retired") return "bg-rose-50 text-rose-700";
  return "bg-slate-100 text-slate-600";
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString();
};

export default function PolicyDetailPage() {
  const params = useParams();
  const idParam = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const parsedId = Number(idParam);
  const policyId = Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null;

  const [policy, setPolicy] = useState<Policy | null>(null);
  const [sections, setSections] = useState<PolicySection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPolicyDetail = async () => {
      if (policyId === null) {
        setError("Invalid policy id.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const [policyData, sectionsData] = await Promise.all([
          getPolicy(policyId),
          getPolicySections(policyId),
        ]);
        setPolicy(policyData);
        setSections(sectionsData.items ?? []);
      } catch (err) {
        logger.error("Failed to load policy detail", err);
        setError("Failed to load policy.");
        handleApiError(err, {
          context: "Policy detail",
          customMessage: "Failed to load policy",
        });
      } finally {
        setLoading(false);
      }
    };

    loadPolicyDetail();
  }, [policyId]);

  if (loading) {
    return <div className="text-sm text-slate-500">Loading policy…</div>;
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="text-sm text-red-600">{error}</div>
        <Link
          href="/compliance/policies"
          className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to policy library
        </Link>
      </div>
    );
  }

  if (!policy) {
    return <div className="text-sm text-slate-500">Policy not found.</div>;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <Link
            href="/compliance/policies"
            className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:underline"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to policy library
          </Link>
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-500" />
            <h1 className="text-2xl font-semibold text-slate-900">
              {policy.name}
            </h1>
          </div>
          <p className="text-sm text-slate-500">{policy.policy_id}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-2 py-1 text-xs font-semibold ${policyStatusStyle(policy.status)}`}
          >
            {(policy.status ?? "draft").replace("_", "")}
          </span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
            {(policy.language ?? "en").toUpperCase()}
          </span>
        </div>
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          Policy metadata
        </h2>
        <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">
              Owner
            </span>
            <div>{policy.owner ?? "—"}</div>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">
              Version
            </span>
            <div>{policy.version ?? "—"}</div>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">
              Effective date
            </span>
            <div>{formatDate(policy.effective_date)}</div>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">
              Last reviewed
            </span>
            <div>{formatDate(policy.last_reviewed_at)}</div>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">
              Updated
            </span>
            <div>{formatDate(policy.updated_at)}</div>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide text-slate-500">
              Source URL
            </span>
            {policy.source_url ? (
              <a
                href={policy.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-indigo-600 hover:underline"
              >
                Open source
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : (
              <div>—</div>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          Final policy content
        </h2>
        {policy.content ? (
          <pre className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">
            {policy.content}
          </pre>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            No top-level policy content is saved yet. Check section content
            below.
          </p>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Layers3 className="h-4 w-4 text-indigo-500" />
          <h2 className="text-sm font-semibold text-slate-900">
            Policy sections
          </h2>
        </div>
        <div className="mt-4 space-y-4">
          {sections.length === 0 ? (
            <p className="text-sm text-slate-500">No sections found.</p>
          ) : (
            sections.map((section) => (
              <article
                key={section.id}
                className="rounded-lg border border-slate-100 bg-slate-50/60 p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">
                    {section.title ?? section.section_ref ?? "Untitled section"}
                  </h3>
                  <span
                    className={`rounded-full px-2 py-1 text-[10px] font-semibold ${policyStatusStyle(section.status)}`}
                  >
                    {(section.status ?? "draft").replace("_", "")}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {section.section_ref ?? "No ref"} • v{section.version ?? "1"}
                </p>
                {section.content ? (
                  <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                    {section.content}
                  </pre>
                ) : (
                  <p className="mt-3 text-sm text-slate-500">
                    No section content provided.
                  </p>
                )}
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

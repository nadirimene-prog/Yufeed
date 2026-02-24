"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { BarChart3, FlaskConical, History, Target } from "lucide-react";
import apiClient from "@/lib/http";
import { useRule } from "@/hooks/queries/useRulesData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import DataTable, { type Column } from "@/components/ui/data-table-horizon";
import { Button } from "@/components/ui/button-horizon";
import { StatusBadge } from "@/components/ui/badge-horizon";

interface BacktestSample {
  transaction_id: string;
  amount: number;
  currency: string;
  transaction_type?: string | null;
  country_code?: string | null;
  timestamp: string;
  would_trigger: boolean;
}

interface RuleBacktestResponse {
  rule_id: string;
  total_transactions: number;
  matches: number;
  match_rate: number;
  evaluated_at: string;
  window: {
    start_date?: string | null;
    end_date?: string | null;
  };
  samples: BacktestSample[];
  precision_estimate?: number;
  recall_estimate?: number;
  false_positive_estimate?: number;
}

function presetWindow(days: 30 | 60 | 90) {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days);
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  };
}

export default function RuleBacktestPage() {
  const params = useParams<{ id: string }>();
  const ruleId = decodeURIComponent(params.id);

  const [windowPreset, setWindowPreset] = useState<30 | 60 | 90>(30);
  const [limit, setLimit] = useState(1000);
  const [sampleSize, setSampleSize] = useState(25);

  const ruleQuery = useRule(ruleId);

  const backtestMutation = useMutation({
    mutationFn: async () => {
      const window = presetWindow(windowPreset);
      const response = await apiClient.post<RuleBacktestResponse>(
        `/api/monitoring-rules/${encodeURIComponent(ruleId)}/backtest`,
        {
          start_date: window.start,
          end_date: window.end,
          limit,
          sample_size: sampleSize,
        },
      );
      return response.data;
    },
  });

  const samples = useMemo(
    () => backtestMutation.data?.samples ?? [],
    [backtestMutation.data?.samples],
  );

  const precisionEstimate =
    backtestMutation.data?.precision_estimate ??
    Math.max(0, 100 - Math.round((backtestMutation.data?.match_rate ?? 0) / 2));
  const recallEstimate =
    backtestMutation.data?.recall_estimate ??
    Math.min(100, Math.round(backtestMutation.data?.match_rate ?? 0));
  const falsePositiveEstimate =
    backtestMutation.data?.false_positive_estimate ??
    Math.max(0, 100 - precisionEstimate);

  const sampleTrend = useMemo(() => {
    if (samples.length === 0) return [{ value: 0 }];
    return samples.map((sample) => ({ value: sample.would_trigger ? 100 : 0 }));
  }, [samples]);

  const columns = useMemo<Column<BacktestSample>[]>(
    () => [
      {
        key: "transaction_id",
        header: "Transaction",
        accessor: (row) => (
          <span className="font-mono text-xs text-foreground">
            {row.transaction_id}
          </span>
        ),
      },
      {
        key: "amount",
        header: "Amount",
        sortable: true,
        accessor: (row) => (
          <span className="text-sm text-foreground-secondary">
            {Number(row.amount).toLocaleString()} {row.currency}
          </span>
        ),
      },
      {
        key: "type",
        header: "Type",
        accessor: (row) => row.transaction_type || "-",
      },
      {
        key: "country",
        header: "Country",
        accessor: (row) => row.country_code || "-",
      },
      {
        key: "timestamp",
        header: "Timestamp",
        sortable: true,
        accessor: (row) => (
          <span className="text-sm text-foreground-secondary">
            {new Date(row.timestamp).toLocaleString()}
          </span>
        ),
      },
      {
        key: "trigger",
        header: "Triggered",
        accessor: (row) => (
          <StatusBadge status={row.would_trigger ? "critical" : "approved"}>
            {row.would_trigger ? "Yes" : "No"}
          </StatusBadge>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-display font-semibold text-foreground">
              Rule Backtesting
            </h1>
            <p className="text-foreground-secondary">
              Simulate <span className="font-mono">{ruleId}</span> against
              historical transactions.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/transaction-monitoring/rules">
              <Button variant="outline">Back to Rules</Button>
            </Link>
            <Button
              onClick={() => backtestMutation.mutate()}
              loading={backtestMutation.isPending}
            >
              <FlaskConical className="h-4 w-4" />
              Run Backtest
            </Button>
          </div>
        </div>
      </header>

      <Card className="border-border shadow-sm bg-white">
        <CardHeader>
          <CardTitle className="text-base text-foreground font-semibold">
            Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <label className="space-y-1 text-xs text-foreground-secondary">
            <span>Window</span>
            <select
              value={windowPreset}
              onChange={(event) =>
                setWindowPreset(Number(event.target.value) as 30 | 60 | 90)
              }
              className="h-10 w-full rounded-lg border border-border bg-slate-50 px-3 text-sm focus:ring-1 focus:ring-primary/20"
            >
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </label>

          <label className="space-y-1 text-xs text-foreground-secondary">
            <span>Transaction Limit</span>
            <input
              type="number"
              min={100}
              max={5000}
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value || 1000))}
              className="h-10 w-full rounded-lg border border-border bg-slate-50 px-3 text-sm focus:ring-1 focus:ring-primary/20"
            />
          </label>

          <label className="space-y-1 text-xs text-foreground-secondary">
            <span>Sample Size</span>
            <input
              type="number"
              min={5}
              max={50}
              value={sampleSize}
              onChange={(event) =>
                setSampleSize(Number(event.target.value || 25))
              }
              className="h-10 w-full rounded-lg border border-border bg-slate-50 px-3 text-sm focus:ring-1 focus:ring-primary/20"
            />
          </label>
        </CardContent>
      </Card>

      <LoadingBoundary
        loading={ruleQuery.isLoading}
        error={ruleQuery.error as Error | undefined}
        isEmpty={!ruleQuery.data}
        emptyMessage="Rule not found"
        emptyDescription="The requested monitoring rule does not exist."
        minHeight="200px"
      >
        <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <MetricCard
            title="Transactions Evaluated"
            value={backtestMutation.data?.total_transactions ?? 0}
            color="cyan"
            icon={<BarChart3 className="h-5 w-5" />}
          />
          <MetricCard
            title="Matches"
            value={backtestMutation.data?.matches ?? 0}
            color="red"
            icon={<Target className="h-5 w-5" />}
            glow
          />
          <MetricCard
            title="Match Rate"
            value={`${(backtestMutation.data?.match_rate ?? 0).toFixed(2)}%`}
            color="orange"
            progress={Math.max(
              0,
              Math.min(100, backtestMutation.data?.match_rate ?? 0),
            )}
            icon={<History className="h-5 w-5" />}
          />
          <MetricCard
            title="Precision Estimate"
            value={`${precisionEstimate.toFixed(1)}%`}
            color={precisionEstimate < 70 ? "yellow" : "green"}
            sparklineData={sampleTrend}
          />
        </section>
      </LoadingBoundary>

      {backtestMutation.data ? (
        <>
          <Card className="border-border shadow-sm bg-white">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base text-foreground font-semibold">
                Simulation Summary
              </CardTitle>
              <StatusBadge status="in_review">
                Evaluated{" "}
                {new Date(backtestMutation.data.evaluated_at).toLocaleString()}
              </StatusBadge>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm text-foreground-secondary md:grid-cols-2">
              <p>
                Window:{" "}
                {new Date(
                  backtestMutation.data.window.start_date ?? "",
                ).toLocaleDateString()}{" "}
                →{" "}
                {new Date(
                  backtestMutation.data.window.end_date ?? "",
                ).toLocaleDateString()}
              </p>
              <p>
                Estimated false positive proxy:{" "}
                {falsePositiveEstimate.toFixed(1)}%
              </p>
              <p>Estimated recall: {recallEstimate.toFixed(1)}%</p>
              <p className="md:text-right">
                Samples returned: {samples.length}
              </p>
            </CardContent>
          </Card>

          <Card className="border-border shadow-sm bg-white">
            <CardHeader>
              <CardTitle className="text-base text-foreground font-semibold">
                Matching Transactions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                data={samples}
                columns={columns}
                keyExtractor={(row) => row.transaction_id}
                pagination
                pageSize={10}
                striped
                bordered
                captionText="Rule backtest sample transactions"
                emptyTitle="No sample transactions"
                emptyDescription="Try increasing the lookback window or lowering rule thresholds."
              />
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

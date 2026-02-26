"use client";

import { use } from "react";
import {
  ArrowLeft,
  MapPin,
  Smartphone,
  Globe,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Flag,
  User,
  ExternalLink,
  History,
} from "lucide-react";

export default function AlertDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      {/* Header / Breadcrumbs */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <a
            href="/transaction-monitoring/dashboard"
            className="rounded-lg p-2 hover:bg-slate-100  transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-slate-500" />
          </a>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 ">
                Alert {id || "AL-8291"}
              </h1>
              <span className="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-bold text-orange-700   uppercase">
                High Risk
              </span>
            </div>
            <p className="text-sm text-slate-500">
              Status:{" "}
              <span className="font-semibold text-blue-600">
                Pending Review
              </span>{" "}
              • Triggered 15m ago
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50   ">
            <XCircle className="h-4 w-4 text-red-500" />
            False Positive
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50   ">
            <Flag className="h-4 w-4 text-orange-500" />
            Escalate
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 shadow-sm transition-all hover:scale-[1.02] active:scale-[0.98]">
            <CheckCircle2 className="h-4 w-4" />
            Resolve Case
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content (Left 2 columns) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Rule Match Details */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm   overflow-hidden">
            <div className="border-b border-slate-100 p-6  bg-slate-50/50 ">
              <h3 className="font-bold text-slate-900  flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-orange-500" />
                Triggering Rule: High Velocity Deposit
              </h3>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-slate-600 ">
                This rule triggers when a user makes more than 3 deposits
                exceeding $1,000 within a 24-hour window.
              </p>

              <div className="rounded-xl border border-blue-100 bg-blue-50/30 p-4  ">
                <h4 className="text-xs font-bold text-blue-900/60  uppercase tracking-widest mb-3">
                  Logic Execution Result
                </h4>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                    <span className="text-sm font-medium text-slate-700 ">
                      Transaction Amount ($5,200.00) {">"} $1,000.00
                    </span>
                    <span className="text-[10px] font-bold text-green-600 bg-green-50 px-1.5 rounded ml-auto">
                      MATCH
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                    <span className="text-sm font-medium text-slate-700 ">
                      24h Deposit Count (4) {">"} 3
                    </span>
                    <span className="text-[10px] font-bold text-green-600 bg-green-50 px-1.5 rounded ml-auto">
                      MATCH
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Transaction History / Timeline */}
          <div className="rounded-2xl border border-slate-200 bg-white shadow-sm   p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-bold text-slate-900  flex items-center gap-2">
                <History className="h-5 w-5 text-blue-500" />
                Activity Timeline
              </h3>
              <button className="text-xs font-bold text-blue-600 hover:text-blue-700 uppercase tracking-wider">
                View Full History
              </button>
            </div>

            <div className="relative space-y-8 before:absolute before:inset-0 before:ml-5 before:h-full before:w-0.5 before:-translate-x-px before:bg-gradient-to-b before:from-blue-200 before:via-slate-100 before:to-transparent  ">
              {/* Timeline Item 1 */}
              <div className="relative flex items-center gap-6">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg ring-4 ring-white ">
                  <ShieldAlert className="h-5 w-5" />
                </div>
                <div className="flex-1 rounded-xl border border-orange-100 bg-orange-50/30 p-4  ">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-slate-900 ">
                      Alert Triggered
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      10:45 AM
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 ">
                    High Velocity Rule detected suspicious pattern in last 4
                    transactions.
                  </p>
                </div>
              </div>

              {/* Timeline Item 2 */}
              <div className="relative flex items-center gap-6">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white border-2 border-slate-200 text-slate-400 shadow  ">
                  <ArrowLeft className="h-5 w-5 rotate-180" />
                </div>
                <div className="flex-1 p-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-900 ">
                      Deposit Received: $5,200.00
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      10:44 AM
                    </span>
                  </div>
                  <div className="flex gap-4 text-[10px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> Paris, FR
                    </span>
                    <span className="flex items-center gap-1">
                      <Smartphone className="h-3 w-3" /> iPhone 15 Pro
                    </span>
                  </div>
                </div>
              </div>

              {/* Timeline Item 3 */}
              <div className="relative flex items-center gap-6">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white border-2 border-slate-200 text-slate-400 shadow  ">
                  <ArrowLeft className="h-5 w-5 rotate-180" />
                </div>
                <div className="flex-1 p-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-900 ">
                      Deposit Received: $1,200.00
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      09:12 AM
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Context (Right 1 column) */}
        <div className="space-y-6">
          {/* Customer Profile Card */}
          <div className="rounded-2xl border border-slate-200 bg-linear-to-b from-slate-50 to-white p-6   ">
            <div className="flex items-center gap-4 mb-6">
              <div className="h-14 w-14 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-xl">
                <User className="h-7 w-7" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-slate-900 ">John Doe</h3>
                <p className="text-xs text-slate-500 font-medium">
                  Customer since Jan 2024
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between items-center py-2 border-b border-slate-100 ">
                <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                  Risk Level
                </span>
                <span className="text-sm font-bold text-orange-600">
                  Medium
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100 ">
                <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                  KYC Status
                </span>
                <span className="text-sm font-bold text-green-600 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Verified
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-100 ">
                <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
                  Total Volume (30d)
                </span>
                <span className="text-sm font-bold text-slate-900 ">
                  $45,200.00
                </span>
              </div>
            </div>

            <button className="w-full mt-6 flex items-center justify-center gap-2 rounded-xl bg-slate-900 py-3 text-sm font-bold text-white hover:bg-black transition-all   ">
              <span>View Full Profile</span>
              <ExternalLink className="h-4 w-4" />
            </button>
          </div>

          {/* Device / Network Insights */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm  ">
            <h3 className="font-bold text-slate-900  mb-4 flex items-center gap-2">
              <Smartphone className="h-4 w-4" />
              Technical Signals
            </h3>
            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="p-2 rounded-lg bg-slate-100  shrink-0">
                  <Globe className="h-4 w-4 text-slate-600" />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-900 ">
                    IP: 192.168.1.105
                  </p>
                  <p className="text-[10px] text-slate-500">
                    Service Provider: Orange SA
                  </p>
                </div>
                <span className="text-[10px] font-bold text-green-600 ml-auto flex items-center gap-1">
                  No Proxy
                </span>
              </div>
              <div className="flex gap-3">
                <div className="p-2 rounded-lg bg-slate-100  shrink-0">
                  <ShieldAlert className="h-4 w-4 text-orange-500" />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-900 ">
                    Rare Device ID
                  </p>
                  <p className="text-[10px] text-slate-500">
                    First time seen for this user
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

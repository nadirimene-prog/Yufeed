"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileSearch, Radar, ShieldCheck, Sparkles } from "lucide-react";
import { AuthError, getAuthToken, loginWithPassword } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";

export default function Home() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [availableTenants, setAvailableTenants] = useState<string[]>([]);
  const [selectedTenant, setSelectedTenant] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorId = error ? "login-error" : undefined;
  const emailInvalid = email.length > 0 && !/^\S+@\S+\.\S+$/.test(email);
  const emailErrorId = emailInvalid ? "login-email-error" : undefined;

  const highlights = [
    {
      icon: Radar,
      title: "Regulatory radar",
      description: "Track EU legal updates and map them to obligations.",
    },
    {
      icon: ShieldCheck,
      title: "AML monitoring",
      description: "Triage alerts with risk context and automated workflows.",
    },
    {
      icon: FileSearch,
      title: "Audit-ready evidence",
      description: "Keep every decision, action, and report traceable.",
    },
  ];

  useEffect(() => {
    if (getAuthToken()) {
      router.replace("/dashboard");
      return;
    }
    setReady(true);
  }, [router]);

  useEffect(() => {
    setAvailableTenants([]);
    setSelectedTenant("");
  }, [email]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await loginWithPassword(email, password, {
        storage: remember ? "local" : "session",
        tenantId: selectedTenant || undefined,
      });
      router.replace("/dashboard");
    } catch (err) {
      const tenants = err instanceof AuthError ? err.availableTenants : undefined;
      if (tenants && tenants.length) {
        setAvailableTenants(tenants);
        setSelectedTenant((prev) => prev || tenants[0] || "");
      }
      const message =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (!ready) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-sm text-muted-foreground">Checking session...</div>
      </div>
    );
  }

  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute -top-24 left-12 h-60 w-60 rounded-full bg-[#6d5acd]/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 right-0 h-72 w-72 rounded-full bg-[#00d4ff]/15 blur-3xl" />

      <div className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.3em] text-[#00d4ff]/80">
              YuFeed Sentinel
            </div>
            <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
              Compliance clarity in minutes, not weeks.
            </h1>
            <p className="text-sm text-muted-foreground md:text-base">
              YuFeed unifies EU regulatory intelligence, AML monitoring, and
              investigation workflows so your team can act with confidence.
            </p>
          </div>

          <div className="space-y-4">
            {highlights.map((item) => (
              <div key={item.title} className="flex gap-3">
                <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-[#00d4ff] shadow-[0_0_20px_rgba(0,212,255,0.12)]">
                  <item.icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground">
                    {item.title}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            {[
              "EU legal coverage",
              "Encrypted at rest",
              "Audit-ready reporting",
              "24/7 monitoring",
            ].map((item) => (
              <span
                key={item}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1"
              >
                {item}
              </span>
            ))}
          </div>
        </div>

        <GlassCard variant="elevated" glow="primary" className="p-8">
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-white/40">
                <Sparkles className="h-4 w-4 text-[#6d5acd]" />
                Secure Console
              </div>
              <h2 className="text-xl font-semibold text-foreground">
                Sign in to your workspace
              </h2>
              <p className="text-sm text-muted-foreground">
                Use your work email to access alerts, cases, and compliance
                reporting.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="block text-xs font-medium text-white/60"
                >
                  Work email
                </label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="name@company.com"
                  autoComplete="email"
                  inputMode="email"
                  error={emailInvalid}
                  errorMessage={emailInvalid ? "Enter a valid work email." : undefined}
                  errorMessageId={emailErrorId}
                  aria-invalid={emailInvalid || Boolean(error)}
                  aria-describedby={[errorId, emailErrorId].filter(Boolean).join(" ") || undefined}
                />
              </div>

              {availableTenants.length > 0 ? (
                <div className="space-y-2">
                  <label
                    htmlFor="tenant"
                    className="block text-xs font-medium text-white/60"
                  >
                    Tenant
                  </label>
                  <select
                    id="tenant"
                    value={selectedTenant}
                    onChange={(event) => setSelectedTenant(event.target.value)}
                    className="h-11 w-full rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-[#6d5acd]"
                    required
                  >
                    {availableTenants.map((tenant) => (
                      <option key={tenant} value={tenant} className="bg-[#0a0a12]">
                        {tenant}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-white/50">
                    Select the workspace you want to access.
                  </p>
                </div>
              ) : null}

              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="block text-xs font-medium text-white/60"
                >
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  error={Boolean(error)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={errorId}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <label className="flex items-center gap-2">
                  <input
                    id="remember"
                    type="checkbox"
                    checked={remember}
                    onChange={(event) => setRemember(event.target.checked)}
                    className="h-4 w-4 rounded border-white/20 bg-white/5"
                  />
                  Keep me signed in on this device
                </label>
                <Link
                  href="/forgot-password"
                  className="text-[#00d4ff]/80 hover:text-[#00d4ff]"
                >
                  Forgot password?
                </Link>
              </div>

              {error ? (
                <div
                  id={errorId}
                  role="alert"
                  aria-live="polite"
                  className="rounded-lg border border-[#ff3366]/30 bg-[#ff3366]/10 px-3 py-2 text-xs text-[#ff99b3]"
                >
                  {error}
                </div>
              ) : null}

              <Button
                type="submit"
                variant="gradient"
                size="lg"
                loading={loading}
                disabled={emailInvalid}
                className="w-full"
              >
                Sign in
              </Button>
            </form>

            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>
                New here?{" "}
                <Link
                  href="/request-access"
                  className="text-[#00d4ff]/80 hover:text-[#00d4ff]"
                >
                  Request access
                </Link>
              </span>
              <span>Need help? support@yufeed.com</span>
            </div>
          </div>
        </GlassCard>
      </div>
    </section>
  );
}

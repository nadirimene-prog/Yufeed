"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileSearch, Radar, ShieldCheck, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { AuthError, getAuthToken, loginWithPassword } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SectionBadge } from "@/components/ui/section-badge";

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
      const tenants =
        err instanceof AuthError ? err.availableTenants : undefined;
      if (tenants?.length) {
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
        <div className="animate-pulse text-sm text-muted-foreground">
          Checking session...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      {/* Hero Section */}
      <section className="relative flex-1 flex flex-col justify-center px-4 py-20 md:px-8 lg:px-12 max-w-7xl mx-auto w-full">
        <div className="grid items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-8"
          >
            <div className="space-y-4">
              <SectionBadge label="YuFeed" />
              <h1 className="text-4xl lg:text-[4.5rem] font-display text-foreground leading-[1.05] tracking-tight">
                Compliance clarity in minutes,{" "}
                <span className="text-gradient relative">
                  not weeks.<span className="gradient-underline"></span>
                </span>
              </h1>
              <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
                YuFeed unifies EU regulatory intelligence, AML monitoring, and
                investigation workflows so your team can act with absolute
                confidence.
              </p>
            </div>

            <div className="flex flex-wrap gap-3 text-sm font-medium text-foreground-secondary">
              {[
                "EU legal coverage",
                "Encrypted at rest",
                "Audit-ready reporting",
                "24/7 monitoring",
              ].map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-border bg-white px-4 py-1.5 shadow-sm"
                >
                  {item}
                </span>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          >
            <Card
              variant="featured"
              className="p-8 sm:p-10 relative overflow-hidden"
            >
              <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-accent opacity-5 blur-[100px]" />

              <div className="space-y-8 relative z-10">
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold text-foreground">
                    Sign in to your workspace
                  </h2>
                  <p className="text-sm text-foreground-secondary">
                    Use your work email to access alerts, cases, and compliance
                    reporting.
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium text-foreground"
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
                      aria-invalid={emailInvalid || Boolean(error)}
                      aria-describedby={
                        [errorId, emailErrorId].filter(Boolean).join(" ") ||
                        undefined
                      }
                      className="h-12 border-border focus:ring-accent"
                    />
                    {emailInvalid && (
                      <p
                        className="text-xs text-destructive mt-1"
                        id={emailErrorId}
                      >
                        Enter a valid work email.
                      </p>
                    )}
                  </div>

                  {availableTenants.length > 0 && (
                    <div className="space-y-2">
                      <label
                        htmlFor="tenant"
                        className="block text-sm font-medium text-foreground"
                      >
                        Tenant
                      </label>
                      <select
                        id="tenant"
                        value={selectedTenant}
                        onChange={(event) =>
                          setSelectedTenant(event.target.value)
                        }
                        className="h-12 w-full rounded-xl border border-border bg-transparent px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 transition-shadow"
                        required
                      >
                        {availableTenants.map((tenant) => (
                          <option key={tenant} value={tenant}>
                            {tenant}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-muted-foreground">
                        Select the workspace you want to access.
                      </p>
                    </div>
                  )}

                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label
                        htmlFor="password"
                        className="block text-sm font-medium text-foreground"
                      >
                        Password
                      </label>
                      <Link
                        href="/forgot-password"
                        className="text-xs font-medium text-accent hover:text-accent-secondary transition-colors"
                      >
                        Forgot password?
                      </Link>
                    </div>
                    <Input
                      id="password"
                      type="password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder="Enter your password"
                      autoComplete="current-password"
                      aria-invalid={Boolean(error)}
                      aria-describedby={errorId}
                      className="h-12 border-border focus:ring-accent"
                    />
                  </div>

                  <div className="flex items-center text-sm text-foreground-secondary">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        id="remember"
                        type="checkbox"
                        checked={remember}
                        onChange={(event) => setRemember(event.target.checked)}
                        className="h-4 w-4 rounded border-border text-accent focus:ring-accent accent-accent transition-colors"
                      />
                      Keep me signed in on this device
                    </label>
                  </div>

                  {error && (
                    <div
                      id={errorId}
                      role="alert"
                      aria-live="polite"
                      className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive font-medium"
                    >
                      {error}
                    </div>
                  )}

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    loading={loading}
                    disabled={emailInvalid}
                    className="w-full h-14"
                    rightIcon={
                      <ArrowRight className="h-4 w-4 opacity-70 group-hover:translate-x-1 transition-transform" />
                    }
                  >
                    Sign in to Workspace
                  </Button>
                </form>

                <div className="flex items-center justify-center gap-1 text-sm text-foreground-secondary pt-2">
                  <span>New here?</span>
                  <Link
                    href="/request-access"
                    className="font-medium text-accent hover:text-accent-secondary transition-colors"
                  >
                    Request access
                  </Link>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Inverted Stats/Features Section */}
      <section className="section-inverted relative overflow-hidden py-24 sm:py-32">
        <div className="absolute inset-0 dot-pattern" />
        <div className="max-w-7xl mx-auto px-4 md:px-8 lg:px-12 relative z-10">
          <div className="grid md:grid-cols-3 gap-12 md:gap-8 divide-y md:divide-y-0 md:divide-x divide-slate-800">
            {highlights.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.6, delay: i * 0.1 }}
                className={`${i > 0 ? "pt-12 md:pt-0 md:pl-8" : ""}`}
              >
                <div className="flex flex-col gap-6">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-[#4D7CFF] shadow-accent text-white">
                    <item.icon className="h-6 w-6" strokeWidth={2.5} />
                  </div>
                  <div>
                    <h3 className="text-xl font-display font-medium text-white mb-2">
                      {item.title}
                    </h3>
                    <p className="text-slate-400 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

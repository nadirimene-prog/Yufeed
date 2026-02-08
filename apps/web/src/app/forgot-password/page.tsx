"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Mail, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const emailInvalid = email.length > 0 && !/^\S+@\S+\.\S+$/.test(email);
  const emailErrorId = emailInvalid ? "forgot-email-error" : undefined;

  const mailto = useMemo(() => {
    const subject = "Password reset request";
    const body = [
      "Please reset the password for the following account:",
      "",
      `Email: ${email || "—"}`,
      `Company: ${company || "—"}`,
      `Role: ${role || "—"}`,
    ].join("\n");
    return `mailto:support@yufeed.com?subject=${encodeURIComponent(
      subject,
    )}&body=${encodeURIComponent(body)}`;
  }, [email, company, role]);

  const handleEmail = () => {
    if (!email) return;
    window.location.href = mailto;
  };

  return (
    <section className="mx-auto max-w-2xl">
      <GlassCard variant="elevated" glow="primary" className="p-8">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-white/40">
              <ShieldCheck className="h-4 w-4 text-[#6d5acd]" />
              Secure recovery
            </div>
            <h1 className="text-2xl font-semibold text-foreground">
              Reset your password
            </h1>
            <p className="text-sm text-muted-foreground">
              For security, password resets are handled by the YuFeed support
              team. Send your work email and we will verify access before
              issuing a reset.
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-muted-foreground">
            Include your work email, company, and role. We respond within one
            business day.
          </div>

          <form className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-xs font-medium text-white/60"
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
                error={emailInvalid}
                errorMessage={
                  emailInvalid ? "Enter a valid work email." : undefined
                }
                errorMessageId={emailErrorId}
                aria-invalid={emailInvalid}
                aria-describedby={emailErrorId}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label
                  htmlFor="company"
                  className="text-xs font-medium text-white/60"
                >
                  Company
                </label>
                <Input
                  id="company"
                  value={company}
                  onChange={(event) => setCompany(event.target.value)}
                  placeholder="Acme Compliance"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="role"
                  className="text-xs font-medium text-white/60"
                >
                  Role
                </label>
                <Input
                  id="role"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  placeholder="Compliance Officer"
                />
              </div>
            </div>
          </form>

          <div className="flex flex-wrap gap-3">
            <Button
              variant="gradient"
              size="lg"
              onClick={handleEmail}
              disabled={!email || emailInvalid}
            >
              <Mail className="h-4 w-4" />
              Email support
            </Button>
            <Button asChild variant="ghost" size="lg">
              <Link href="/">Back to sign in</Link>
            </Button>
          </div>
        </div>
      </GlassCard>
    </section>
  );
}

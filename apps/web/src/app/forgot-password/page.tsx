"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Mail, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
      <Card className="p-8 border-border shadow-md">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-primary" />
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

          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground">
            Include your work email, company, and role. We respond within one
            business day.
          </div>

          <form className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-xs font-medium text-muted-foreground"
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
                className="bg-slate-50"
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label
                  htmlFor="company"
                  className="text-xs font-medium text-muted-foreground"
                >
                  Company
                </label>
                <Input
                  id="company"
                  value={company}
                  onChange={(event) => setCompany(event.target.value)}
                  placeholder="Acme Compliance"
                  className="bg-slate-50"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="role"
                  className="text-xs font-medium text-muted-foreground"
                >
                  Role
                </label>
                <Input
                  id="role"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  placeholder="Compliance Officer"
                  className="bg-slate-50"
                />
              </div>
            </div>
          </form>

          <div className="flex flex-wrap gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={handleEmail}
              disabled={!email || emailInvalid}
            >
              <Mail className="h-4 w-4 mr-2" />
              Email support
            </Button>
            <Link href="/">
              <Button variant="outline" size="lg">
                Back to sign in
              </Button>
            </Link>
          </div>
        </div>
      </Card>
    </section>
  );
}

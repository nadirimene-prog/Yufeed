"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Building2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";

export default function RequestAccessPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [notes, setNotes] = useState("");
  const emailInvalid = email.length > 0 && !/^\S+@\S+\.\S+$/.test(email);
  const emailErrorId = emailInvalid ? "request-email-error" : undefined;

  const mailto = useMemo(() => {
    const subject = "YuFeed access request";
    const body = [
      "Please grant access for:",
      "",
      `Name: ${name || "—"}`,
      `Work email: ${email || "—"}`,
      `Company: ${company || "—"}`,
      `Role: ${role || "—"}`,
      `Jurisdiction: ${jurisdiction || "—"}`,
      `Notes: ${notes || "—"}`,
    ].join("\n");
    return `mailto:support@yufeed.com?subject=${encodeURIComponent(
      subject,
    )}&body=${encodeURIComponent(body)}`;
  }, [name, email, company, role, jurisdiction, notes]);

  const handleEmail = () => {
    if (!email || !name) return;
    window.location.href = mailto;
  };

  return (
    <section className="mx-auto max-w-2xl">
      <Card className="p-8 border-border shadow-md bg-white">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              <Building2 className="h-4 w-4 text-primary" />
              Workspace access
            </div>
            <h1 className="text-2xl font-semibold text-foreground">
              Request access to YuFeed
            </h1>
            <p className="text-sm text-muted-foreground">
              Tell us about your organization and role. We will confirm your
              compliance scope and provision your workspace.
            </p>
          </div>

          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground">
            Required details: name, work email, company, role, and jurisdiction.
            This helps us configure the right compliance modules.
          </div>

          <form className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label
                  htmlFor="name"
                  className="text-xs font-medium text-muted-foreground"
                >
                  Full name
                </label>
                <Input
                  id="name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Ava Lawrence"
                  required
                  className="bg-slate-50 border-border focus:ring-1 focus:ring-primary/20"
                />
              </div>
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
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="name@company.com"
                  autoComplete="email"
                  required
                  error={emailInvalid}
                  errorMessage={
                    emailInvalid ? "Enter a valid work email." : undefined
                  }
                  errorMessageId={emailErrorId}
                  aria-invalid={emailInvalid}
                  aria-describedby={emailErrorId}
                  className="bg-slate-50 border-border focus:ring-1 focus:ring-primary/20"
                />
              </div>
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
                  className="bg-slate-50 border-border focus:ring-1 focus:ring-primary/20"
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
                  className="bg-slate-50 border-border focus:ring-1 focus:ring-primary/20"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label
                htmlFor="jurisdiction"
                className="text-xs font-medium text-muted-foreground"
              >
                Jurisdiction
              </label>
              <Input
                id="jurisdiction"
                value={jurisdiction}
                onChange={(event) => setJurisdiction(event.target.value)}
                placeholder="EU / UK / Global"
                className="bg-slate-50 border-border focus:ring-1 focus:ring-primary/20"
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="notes"
                className="text-xs font-medium text-muted-foreground"
              >
                Notes (optional)
              </label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Tell us about your compliance scope or timelines."
                className="bg-slate-50 border-border focus:ring-1 focus:ring-primary/20 min-h-[100px]"
              />
            </div>
          </form>

          <div className="flex flex-wrap gap-3">
            <Button
              variant="primary"
              size="lg"
              onClick={handleEmail}
              disabled={!name || !email || emailInvalid}
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

import { Bell, KeyRound, Settings, User } from "lucide-react";
import {
  GlassCard,
  GlassCardContent,
  GlassCardDescription,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">
          Settings
        </h1>
        <p className="mt-2 text-sm text-white/60">
          Manage your account, notifications, and system preferences.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <GlassCard
          variant="surface"
          className="bg-white/[0.02] border border-white/[0.06]"
        >
          <GlassCardHeader>
            <GlassCardTitle className="flex items-center gap-2">
              <User className="h-4 w-4 text-[#00d4ff]" />
              Account
            </GlassCardTitle>
            <GlassCardDescription>
              Profile details, security, and session controls.
            </GlassCardDescription>
          </GlassCardHeader>
          <GlassCardContent className="text-sm text-white/70">
            Coming soon.
          </GlassCardContent>
        </GlassCard>

        <GlassCard
          variant="surface"
          className="bg-white/[0.02] border border-white/[0.06]"
        >
          <GlassCardHeader>
            <GlassCardTitle className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-[#6d5acd]" />
              Notifications
            </GlassCardTitle>
            <GlassCardDescription>
              Real-time alerts and email preferences.
            </GlassCardDescription>
          </GlassCardHeader>
          <GlassCardContent className="text-sm text-white/70">
            Coming soon.
          </GlassCardContent>
        </GlassCard>

        <GlassCard
          variant="surface"
          className="bg-white/[0.02] border border-white/[0.06]"
        >
          <GlassCardHeader>
            <GlassCardTitle className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-[#06d6a0]" />
              API
            </GlassCardTitle>
            <GlassCardDescription>
              API keys and integration settings.
            </GlassCardDescription>
          </GlassCardHeader>
          <GlassCardContent className="text-sm text-white/70">
            Coming soon.
          </GlassCardContent>
        </GlassCard>

        <GlassCard
          variant="surface"
          className="bg-white/[0.02] border border-white/[0.06]"
        >
          <GlassCardHeader>
            <GlassCardTitle className="flex items-center gap-2">
              <Settings className="h-4 w-4 text-white/70" />
              System
            </GlassCardTitle>
            <GlassCardDescription>
              Workspace defaults and administrative preferences.
            </GlassCardDescription>
          </GlassCardHeader>
          <GlassCardContent className="text-sm text-white/70">
            Coming soon.
          </GlassCardContent>
        </GlassCard>
      </div>
    </div>
  );
}

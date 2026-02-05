import { Mail, ShieldCheck, User } from "lucide-react";
import { GlassCard, GlassCardContent, GlassCardDescription, GlassCardHeader, GlassCardTitle } from "@/components/ui/glass-card";

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Profile</h1>
        <p className="mt-2 text-sm text-white/60">Your identity and access context in YuFeed Sentinel.</p>
      </div>

      <GlassCard variant="surface" className="bg-white/[0.02] border border-white/[0.06]">
        <GlassCardHeader>
          <GlassCardTitle className="flex items-center gap-2">
            <User className="h-4 w-4 text-[#00d4ff]" />
            Admin User
          </GlassCardTitle>
          <GlassCardDescription>Workspace member</GlassCardDescription>
        </GlassCardHeader>
        <GlassCardContent className="grid gap-3 text-sm">
          <div className="flex items-center gap-2 text-white/70">
            <Mail className="h-4 w-4 text-white/40" />
            <span className="font-mono text-xs">admin@yufeed.eu</span>
          </div>
          <div className="flex items-center gap-2 text-white/70">
            <ShieldCheck className="h-4 w-4 text-[#06d6a0]" />
            <span>Role: Admin</span>
          </div>
          <div className="text-xs text-white/50">
            This is a placeholder profile page to prevent dead navigation. Wire up user data once auth/identity is
            connected.
          </div>
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}


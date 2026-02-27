import { Bell, KeyRound, Settings, User } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Settings
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Configure your profile, notification preferences, integrations, and
          workspace defaults.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <User className="h-4 w-4 text-primary" />
              Account
            </CardTitle>
            <CardDescription>
              Manage your profile details, login security, and active sessions.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Available soon.
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <Bell className="h-4 w-4 text-blue-500" />
              Notifications
            </CardTitle>
            <CardDescription>
              Choose which alerts you receive in-app and by email, and set quiet
              hours.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Available soon.
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <KeyRound className="h-4 w-4 text-green-500" />
              API
            </CardTitle>
            <CardDescription>
              Generate API keys and configure third-party integrations.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Available soon.
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <Settings className="h-4 w-4 text-slate-500" />
              System
            </CardTitle>
            <CardDescription>
              Set workspace-wide defaults, roles, and administrative controls.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Available soon.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

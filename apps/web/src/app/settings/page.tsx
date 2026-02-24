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
          Manage your account, notifications, and system preferences.
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
              Profile details, security, and session controls.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Coming soon.
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <Bell className="h-4 w-4 text-purple-500" />
              Notifications
            </CardTitle>
            <CardDescription>
              Real-time alerts and email preferences.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Coming soon.
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <KeyRound className="h-4 w-4 text-green-500" />
              API
            </CardTitle>
            <CardDescription>
              API keys and integration settings.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Coming soon.
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-foreground font-semibold">
              <Settings className="h-4 w-4 text-slate-500" />
              System
            </CardTitle>
            <CardDescription>
              Workspace defaults and administrative preferences.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Coming soon.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

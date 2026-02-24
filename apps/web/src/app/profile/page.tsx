import { Mail, ShieldCheck, User } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Profile
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your identity and access context in YuFeed Sentinel.
        </p>
      </div>

      <Card className="border-border shadow-sm bg-white">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-foreground">
            <User className="h-4 w-4 text-primary" />
            Admin User
          </CardTitle>
          <CardDescription>Workspace member</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Mail className="h-4 w-4 text-muted-foreground/50" />
            <span className="font-mono text-xs text-foreground">
              admin@yufeed.eu
            </span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-green-500" />
            <span className="text-foreground">Role: Admin</span>
          </div>
          <div className="text-xs text-muted-foreground/70">
            This is a placeholder profile page to prevent dead navigation. Wire
            up user data once auth/identity is connected.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

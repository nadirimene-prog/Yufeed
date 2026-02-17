import { redirect } from "next/navigation";

export default function MonitoringRedirectPage() {
  redirect("/dashboard?view=monitoring");
}

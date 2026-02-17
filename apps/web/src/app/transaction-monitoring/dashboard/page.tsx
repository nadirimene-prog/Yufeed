import { redirect } from "next/navigation";

export default function TransactionMonitoringDashboardRedirectPage() {
  redirect("/dashboard?view=monitoring");
}

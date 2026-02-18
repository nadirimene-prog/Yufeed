import { redirect } from "next/navigation";

export default function ComplianceDashboardRedirectPage() {
  redirect("/dashboard?view=compliance");
}

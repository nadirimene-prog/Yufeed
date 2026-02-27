export default function DashboardLoading() {
  return (
    <div className="space-y-3 p-4">
      <div className="h-10 animate-pulse rounded-lg bg-muted" />
      <div className="grid gap-3 lg:grid-cols-[420px_minmax(0,1fr)_320px]">
        <div className="h-[65vh] animate-pulse rounded-xl bg-muted" />
        <div className="h-[65vh] animate-pulse rounded-xl bg-muted" />
        <div className="h-[65vh] animate-pulse rounded-xl bg-muted" />
      </div>
    </div>
  );
}

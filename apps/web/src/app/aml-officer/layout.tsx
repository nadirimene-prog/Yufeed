export default function AMLOfficerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen">
      <main>{children}</main>
    </div>
  );
}

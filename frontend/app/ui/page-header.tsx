export default function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <header className="mb-6 border-b border-ink pb-4">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {description && <p className="mt-1 text-sm text-muted">{description}</p>}
    </header>
  );
}

export default function Notice({ title, message, children }: { title: string; message: string; children?: React.ReactNode }) {
  return (
    <div className="border border-ink bg-panel p-5">
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted">{message}</p>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

export const buttonClass = "inline-block border border-ink bg-ink px-4 py-2 text-sm font-medium text-panel hover:bg-ink/85 disabled:opacity-50";

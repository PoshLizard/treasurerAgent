// Square line caps and mitered corners keep the icons as boxy as the rest of the UI
function Icon({ children, className = "size-[18px]" }: { children: React.ReactNode; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="square"
      strokeLinejoin="miter" aria-hidden="true" className={className}>
      {children}
    </svg>
  );
}

export function CubeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-6">
      <path d="M12 2 21 7v10l-9 5-9-5V7z" fill="var(--color-panel)" stroke="currentColor" strokeWidth={1.75} />
      <path d="M12 2 21 7l-9 5-9-5z" fill="currentColor" />
      <path d="M12 12v10" stroke="currentColor" strokeWidth={1.75} />
    </svg>
  );
}

export function ReceiptIcon() {
  return <Icon><path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" /><path d="M9 8h6M9 12h6" /></Icon>;
}

export function ChatIcon() {
  return <Icon><path d="M4 4h16v12H9l-5 4z" /></Icon>;
}

export function ArchiveIcon() {
  return <Icon><path d="M3 4h18v5H3zM5 9v11h14V9M10 13h4" /></Icon>;
}

export function UploadIcon() {
  return <Icon className="size-7"><path d="M12 15V4M7 9l5-5 5 5M4 20h16" /></Icon>;
}

// motion-safe: people who turn on "reduce motion" in their OS get the static version

const RECEIPT_LINE_WIDTHS = ["80%", "55%", "70%", "45%", "65%", "35%", "60%"];

// A receipt with a scan line sweeping over it, shown while Gemini reads the photo
export function ScanLoader({ label }: { label: string }) {
  return (
    <div role="status" className="flex flex-col items-center gap-4 border border-ink bg-panel px-6 py-10">
      <div className="relative h-40 w-32 overflow-hidden border-2 border-ink bg-paper">
        <div className="space-y-2.5 p-3">
          {RECEIPT_LINE_WIDTHS.map((width, index) => (
            <div key={index} className="h-1.5 bg-line-strong" style={{ width }} />
          ))}
        </div>
        <div className="absolute inset-x-0 top-0 h-[3px] bg-ink motion-safe:animate-scan" />
      </div>
      <p className="text-sm font-medium">{label}</p>
    </div>
  );
}

export function SquaresLoader({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-sm">
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((index) => (
          <span key={index} className="size-2.5 bg-ink motion-safe:animate-blink" style={{ animationDelay: `${index * 0.2}s` }} />
        ))}
      </span>
      {label}
    </div>
  );
}

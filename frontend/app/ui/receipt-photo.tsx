"use client";
import { useState } from "react";

export default function ReceiptPhoto({ receiptId, alt }: { receiptId: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  // Our own route, which redirects to a fresh link each time, so this never goes stale
  const src = `/api/receipts/${receiptId}/photo`;

  return (
    <figure className="border border-ink bg-panel lg:sticky lg:top-10">
      {failed ? (
        <p className="p-6 text-sm text-muted">
          Couldn&apos;t show the photo. Try reloading the page. HEIC photos only display in Safari.
        </p>
      ) : (
        // A plain img, not next/image: Next's optimizer would cache a copy of a private photo
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={alt} onError={() => setFailed(true)} className="mx-auto block max-h-[80dvh] w-auto" />
      )}
      <figcaption className="flex justify-between border-t border-ink px-3 py-2 text-xs text-muted">
        <span>Original photo</span>
        <a href={src} target="_blank" rel="noopener noreferrer" className="underline hover:text-ink">
          Open full size
        </a>
      </figcaption>
    </figure>
  );
}

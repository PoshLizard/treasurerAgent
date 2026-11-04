"use client";
import { useState } from "react";

export default function ReceiptPhoto({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);

  return (
    <figure className="border border-ink bg-panel lg:sticky lg:top-10">
      {failed ? (
        <p className="p-6 text-sm text-muted">
          Couldn&apos;t show the photo. The link expires after 10 minutes, so reload the page. HEIC photos
          only display in Safari.
        </p>
      ) : (
        // A plain img, not next/image: the link expires in minutes, so optimizing and caching it is pointless
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

"use client";
import Link from "next/link";
import { useState } from "react";
import type { ReceiptResult } from "../lib/receipts";
import { UploadIcon } from "./icons";
import { ScanLoader } from "./loaders";
import ReceiptCard from "./receipt-card";
import { useToast } from "./toast";

const MAX_EDGE_PIXELS = 2000; // high enough to keep the small print on long receipts readable
const JPEG_QUALITY = 0.85;
// Vercel rejects bodies over 4.5 MB, and proxy.ts silently cuts off bodies over 10 MB
const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;

// The formats the backend accepts
const EXTENSION_TYPES: Record<string, string> = {
  jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", heic: "image/heic", heif: "image/heif",
};
const SUPPORTED_TYPES = new Set(Object.values(EXTENSION_TYPES));

// Returns the photo's type, or null if the backend won't accept it
function imageType(file: File): string | null {
  if (SUPPORTED_TYPES.has(file.type)) return file.type;
  // Some browsers report HEIC photos with no type, so fall back to the file extension
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return file.type === "" ? (EXTENSION_TYPES[extension] ?? null) : null;
}

async function shrinkImage(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_EDGE_PIXELS / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Couldn't shrink image"))),
      "image/jpeg",
      JPEG_QUALITY,
    );
  });
}

export default function ReceiptUpload() {
  const [result, setResult] = useState<ReceiptResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const showToast = useToast();

  async function uploadReceipt(file: File) {
    const type = imageType(file);
    if (!type) {
      showToast(`"${file.name}" isn't a supported format. Choose a JPEG, PNG, WebP or HEIC photo.`);
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      // Some browsers can't decode HEIC photos, so those go up unchanged
      const image = await shrinkImage(file).catch(() => new Blob([file], { type }));
      if (image.size > MAX_UPLOAD_BYTES) {
        showToast("That photo is too large to upload. Try a smaller one.");
        return;
      }

      const formData = new FormData();
      formData.append("image", image, "receipt");
      const response = await fetch("/api/receipts", { method: "POST", body: formData });
      // Errors from the hosting platform aren't JSON, so the body may not parse
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        showToast(typeof data?.detail === "string" ? data.detail : "Couldn't process that receipt. Try again.");
        return;
      }
      setResult(data);
    } catch {
      showToast("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <input
          id="receipt-photo"
          type="file"
          accept="image/*"
          className="peer sr-only"
          disabled={loading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = ""; // so choosing the same photo again still fires onChange
            if (file) uploadReceipt(file);
          }}
        />
        <label
          htmlFor="receipt-photo"
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file && !loading) uploadReceipt(file);
          }}
          className={`flex cursor-pointer flex-col items-center gap-2 border-2 border-dashed px-6 py-10 text-center peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ink peer-disabled:cursor-not-allowed peer-disabled:opacity-50 ${
            dragging ? "border-ink bg-sand" : "border-line-strong bg-panel hover:border-ink"
          }`}
        >
          <UploadIcon />
          <span className="font-semibold">Choose a receipt photo</span>
          <span className="text-sm text-muted">
            <span className="hidden sm:inline">or drag one here · </span>JPEG, PNG, WebP or HEIC
          </span>
        </label>
      </div>

      {loading && <ScanLoader label="Reading the receipt and checking the math" />}

      {result && (
        <section>
          <div className="mb-3 flex items-center justify-between gap-4 text-sm">
            <p className="text-muted">Saved for review.</p>
            <Link href={`/receipts/${result.id}`} className="font-medium underline underline-offset-4 hover:no-underline">
              View with photo →
            </Link>
          </div>
          <ReceiptCard receipt={result.receipt} issues={result.issues} status="needs_review" />
        </section>
      )}
    </div>
  );
}

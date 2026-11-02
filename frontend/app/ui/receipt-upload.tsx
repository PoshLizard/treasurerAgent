"use client";
import { useEffect, useState } from "react";

type LineItem = {
  raw_text: string;
  item_code: string | null;
  quantity: string;
  unit_price: string | null;
  line_total: string;
};
type Receipt = {
  merchant: string | null;
  purchase_date: string | null;
  items: LineItem[];
  subtotal: string | null;
  tax: string | null;
  tip: string | null;
  total: string | null;
};
type ReceiptResult = { id: string; receipt: Receipt; issues: string[] };
type SavedReceipt = {
  id: string;
  merchant: string | null;
  purchase_date: string | null;
  total: string | null;
  status: string;
  issues: string[];
};

const MAX_EDGE_PIXELS = 2000; // high enough to keep the small print on long receipts readable
const JPEG_QUALITY = 0.85;
// Vercel rejects bodies over 4.5 MB, and proxy.ts silently cuts off bodies over 10 MB
const MAX_UPLOAD_BYTES = 4 * 1024 * 1024;

const dollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const formatMoney = (amount: string | null) => (amount === null ? "Not shown" : dollars.format(Number(amount)));

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

async function fetchSavedReceipts(): Promise<SavedReceipt[]> {
  const response = await fetch("/api/receipts");
  if (!response.ok) throw new Error("Failed to load receipts");
  return response.json();
}

export default function ReceiptUpload() {
  const [result, setResult] = useState<ReceiptResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedReceipt[] | null>(null);
  const [savedError, setSavedError] = useState(false);

  function loadSaved() {
    return fetchSavedReceipts().then(
      (receipts) => {
        setSaved(receipts);
        setSavedError(false);
      },
      () => setSavedError(true),
    );
  }

  useEffect(() => {
    fetchSavedReceipts().then(setSaved, () => setSavedError(true));
  }, []);

  async function uploadReceipt(file: File) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      // Some browsers can't decode HEIC photos, so those go up unchanged
      const image = await shrinkImage(file).catch(() => file);
      if (image.size > MAX_UPLOAD_BYTES) {
        setError("That photo is too large to upload. Try a smaller one.");
        return;
      }

      const formData = new FormData();
      formData.append("image", image, "receipt");
      const response = await fetch("/api/receipts", { method: "POST", body: formData });
      // Errors from the hosting platform aren't JSON, so the body may not parse
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        setError(data?.detail || "Couldn't process that receipt");
        return;
      }
      setResult(data);
      await loadSaved();
    } catch {
      setError("Couldn't reach server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <label className="block font-bold mb-2" htmlFor="receipt-photo">
        Receipt photo
      </label>
      <input
        id="receipt-photo"
        type="file"
        accept="image/*"
        disabled={loading}
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = ""; // so choosing the same photo again still fires onChange
          if (file) uploadReceipt(file);
        }}
      ></input>

      {loading && <p className="mt-4">Reading receipt...</p>}
      {error && <p className="mt-4 text-red-500">{error}</p>}
      {result && (
        <div className="mt-6">
          {result.issues.length > 0 ? (
            <div className="p-4 mb-4 rounded-lg border border-yellow-500">
              <p className="font-bold">Needs review:</p>
              <ul className="list-disc pl-5">
                {result.issues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mb-4 font-bold text-green-600">All checks passed</p>
          )}

          <p className="font-bold">{result.receipt.merchant ?? "Unknown store"}</p>
          <p className="mb-4">{result.receipt.purchase_date ?? "Unknown date"}</p>

          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-300">
                <th className="py-2 pr-3">Item</th>
                <th className="py-2 pr-3">Code</th>
                <th className="py-2 pr-3">Qty</th>
                <th className="py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {result.receipt.items.map((item, index) => (
                <tr key={index} className="border-b border-gray-200">
                  <td className="py-2 pr-3">{item.raw_text}</td>
                  <td className="py-2 pr-3 break-all">{item.item_code}</td>
                  <td className="py-2 pr-3">{Number(item.quantity)}</td>
                  <td className="py-2 text-right">{formatMoney(item.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <dl className="mt-4 ml-auto max-w-xs">
            {(["subtotal", "tax", "tip", "total"] as const).map((field) => (
              <div key={field} className="flex justify-between">
                <dt className="capitalize">{field}</dt>
                <dd>{formatMoney(result.receipt[field])}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="mt-8">
        <h2 className="text-xl font-bold mb-2">Saved receipts</h2>
        {savedError && <p className="text-red-500">Couldn&apos;t load saved receipts</p>}
        {saved?.length === 0 && <p>Nothing saved yet.</p>}
        <ul>
          {saved?.map((receipt) => (
            <li key={receipt.id} className="flex justify-between gap-3 py-2 border-b border-gray-200">
              <div>
                <p>{receipt.merchant ?? "Unknown store"}</p>
                <p className="text-sm text-gray-500">
                  {receipt.purchase_date ?? "Unknown date"}
                  {receipt.status === "approved" ? " · Approved" : " · Needs review"}
                  {receipt.issues.length > 0 && ` · ${receipt.issues.length} flagged`}
                </p>
              </div>
              <p>{formatMoney(receipt.total)}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

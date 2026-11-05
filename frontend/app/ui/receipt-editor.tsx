"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Receipt, ReceiptDetail } from "../lib/receipts";
import { buttonClass } from "./notice";
import ReceiptCard from "./receipt-card";
import { useToast } from "./toast";

// The form keeps every value as text, the way the inputs hold it, and converts back on save
type ItemDraft = { raw_text: string; item_code: string; quantity: string; unit_price: string; line_total: string };
type Draft = Record<"merchant" | "purchase_date" | "subtotal" | "tax" | "tip" | "total", string> & { items: ItemDraft[] };

const MONEY_FIELDS = ["subtotal", "tax", "tip", "total"] as const;
const EMPTY_ITEM: ItemDraft = { raw_text: "", item_code: "", quantity: "1", unit_price: "", line_total: "" };

const orNull = (value: string) => (value.trim() === "" ? null : value.trim());

function toDraft(receipt: Receipt): Draft {
  return {
    merchant: receipt.merchant ?? "",
    purchase_date: receipt.purchase_date ?? "",
    items: receipt.items.map((item) => ({
      raw_text: item.raw_text, item_code: item.item_code ?? "", quantity: item.quantity,
      unit_price: item.unit_price ?? "", line_total: item.line_total,
    })),
    subtotal: receipt.subtotal ?? "", tax: receipt.tax ?? "", tip: receipt.tip ?? "", total: receipt.total ?? "",
  };
}

function fromDraft(draft: Draft) {
  return {
    merchant: orNull(draft.merchant),
    purchase_date: orNull(draft.purchase_date),
    items: draft.items.map((item) => ({
      raw_text: item.raw_text.trim(), item_code: orNull(item.item_code), quantity: orNull(item.quantity) ?? "1",
      unit_price: orNull(item.unit_price), line_total: item.line_total.trim(),
    })),
    subtotal: orNull(draft.subtotal), tax: orNull(draft.tax), tip: orNull(draft.tip), total: orNull(draft.total),
  };
}

const inputClass = "w-full min-w-0 border border-line-strong bg-paper px-2 py-1.5 text-sm";
const secondaryButtonClass = "inline-block border border-ink px-4 py-2 text-sm font-medium hover:bg-sand disabled:opacity-50";

function Field({ label, className = "", ...input }: { label: string; className?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={`block text-xs text-muted ${className}`}>
      {label}
      <input className={`${inputClass} mt-1 text-ink`} {...input} />
    </label>
  );
}

export default function ReceiptEditor({ initial }: { initial: ReceiptDetail }) {
  const [detail, setDetail] = useState(initial);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const showToast = useToast();

  const setField = (field: keyof Omit<Draft, "items">, value: string) => setDraft((d) => d && { ...d, [field]: value });
  const setItem = (index: number, field: keyof ItemDraft, value: string) =>
    setDraft((d) => d && { ...d, items: d.items.map((item, i) => (i === index ? { ...item, [field]: value } : item)) });

  async function save() {
    if (!draft) return;
    if (draft.items.some((item) => !item.raw_text.trim() || !item.line_total.trim())) {
      showToast("Every item needs a name and an amount.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch(`/api/receipts/${detail.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fromDraft(draft)),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        // FastAPI describes invalid input as a list, not a sentence
        const invalid = response.status === 422 && typeof data?.detail !== "string";
        showToast(invalid ? "Some values aren't valid. Amounts and quantities must be numbers." : data?.detail || "Couldn't save your changes.");
        return;
      }
      setDetail(data);
      setDraft(null);
      router.refresh(); // so the saved receipts list shows the change too
    } catch {
      showToast("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      const response = await fetch(`/api/receipts/${detail.id}`, { method: "DELETE" });
      if (!response.ok && response.status !== 404) {
        const data = await response.json().catch(() => null);
        showToast(data?.detail || "Couldn't delete that receipt.");
        setBusy(false);
        return;
      }
      router.replace("/receipts"); // replace: Back shouldn't return to a receipt that no longer exists
    } catch {
      showToast("Couldn't reach the server. Check your connection and try again.");
      setBusy(false);
    }
  }

  if (!draft) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-end gap-2">
          {confirmingDelete ? (
            <div role="group" aria-label="Confirm delete" className="flex w-full flex-wrap items-center justify-between gap-2 border-2 border-error bg-panel p-3">
              <p className="text-sm">Delete this receipt and its photo? This can&apos;t be undone.</p>
              <div className="flex gap-2">
                <button type="button" onClick={() => setConfirmingDelete(false)} className={secondaryButtonClass} disabled={busy}>Cancel</button>
                <button type="button" onClick={remove} disabled={busy}
                  className="border border-error bg-error px-4 py-2 text-sm font-medium text-panel hover:opacity-90 disabled:opacity-50">
                  {busy ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          ) : (
            <>
              <button type="button" onClick={() => setDraft(toDraft(detail.receipt))} className={buttonClass}>Edit</button>
              <button type="button" onClick={() => setConfirmingDelete(true)} className={secondaryButtonClass}>Delete</button>
            </>
          )}
        </div>
        <ReceiptCard receipt={detail.receipt} issues={detail.issues} status={detail.status} />
      </div>
    );
  }

  return (
    <form
      className="border border-ink bg-panel"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <div className="grid gap-3 border-b border-ink p-4 sm:grid-cols-[1fr_auto] sm:p-5">
        <Field label="Store" value={draft.merchant} onChange={(e) => setField("merchant", e.target.value)} />
        <Field label="Date" type="date" value={draft.purchase_date} onChange={(e) => setField("purchase_date", e.target.value)} />
      </div>

      <ol className="divide-y divide-line">
        {draft.items.map((item, index) => (
          <li key={index} className="space-y-2 px-4 py-3 sm:px-5">
            <div className="flex items-end gap-2">
              <Field label={`Item ${index + 1}`} className="flex-1" value={item.raw_text}
                onChange={(e) => setItem(index, "raw_text", e.target.value)} />
              <button type="button" aria-label={`Remove item ${index + 1}`} title="Remove item"
                onClick={() => setDraft((d) => d && { ...d, items: d.items.filter((_, i) => i !== index) })}
                className="border border-line-strong px-3 py-1.5 text-sm text-muted hover:border-error hover:text-error">
                ×
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Field label="Code" value={item.item_code} onChange={(e) => setItem(index, "item_code", e.target.value)} />
              <Field label="Qty" inputMode="decimal" value={item.quantity} onChange={(e) => setItem(index, "quantity", e.target.value)} />
              <Field label="Unit price" inputMode="decimal" value={item.unit_price} onChange={(e) => setItem(index, "unit_price", e.target.value)} />
              <Field label="Amount" inputMode="decimal" value={item.line_total} onChange={(e) => setItem(index, "line_total", e.target.value)} />
            </div>
          </li>
        ))}
      </ol>
      <div className="border-t border-line px-4 py-3 sm:px-5">
        <button type="button" onClick={() => setDraft((d) => d && { ...d, items: [...d.items, { ...EMPTY_ITEM }] })}
          className="text-sm font-medium underline underline-offset-4 hover:no-underline">
          + Add item
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-ink p-4 sm:grid-cols-4 sm:p-5">
        {MONEY_FIELDS.map((field) => (
          <Field key={field} label={field[0].toUpperCase() + field.slice(1)} inputMode="decimal" value={draft[field]}
            onChange={(e) => setField(field, e.target.value)} />
        ))}
      </div>

      <div className="flex justify-end gap-2 border-t border-ink p-4 sm:px-5">
        <button type="button" onClick={() => setDraft(null)} className={secondaryButtonClass} disabled={busy}>Cancel</button>
        <button type="submit" className={buttonClass} disabled={busy}>{busy ? "Saving..." : "Save changes"}</button>
      </div>
    </form>
  );
}

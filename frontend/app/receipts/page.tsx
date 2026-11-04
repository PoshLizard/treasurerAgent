import type { Metadata } from "next";
import Link from "next/link";
import { backendFetch } from "../lib/backend";
import { formatDate, formatMoney, type ReceiptSummary } from "../lib/receipts";
import Notice, { buttonClass } from "../ui/notice";
import PageHeader from "../ui/page-header";
import { StatusBadge } from "../ui/receipt-card";

export const metadata: Metadata = { title: "Saved receipts" };

// A Server Component: it calls the backend directly, and loading.tsx shows while it waits
export default async function SavedReceiptsPage() {
  const response = await backendFetch("/receipts");
  if (!response.ok) {
    return <Notice title="Couldn't load saved receipts" message="Try again in a minute." />;
  }
  const receipts: ReceiptSummary[] = await response.json();

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Saved receipts" description="Newest first. Select a receipt to see its breakdown and photo." />
      {receipts.length === 0 ? (
        <Notice title="No receipts yet" message="Receipts you process are saved here for review.">
          <Link href="/" className={buttonClass}>Process a receipt</Link>
        </Notice>
      ) : (
        <ul className="border border-ink bg-panel">
          {receipts.map((receipt) => (
            <li key={receipt.id} className="border-b border-line last:border-b-0">
              <Link
                href={`/receipts/${receipt.id}`}
                className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 px-4 py-3 hover:bg-sand sm:px-5"
              >
                <span className="truncate font-medium">{receipt.merchant ?? "Unknown store"}</span>
                <span className="font-mono tabular-nums">{formatMoney(receipt.total)}</span>
                <span className="text-sm text-muted">
                  {formatDate(receipt.purchase_date)}
                  {receipt.issues.length > 0 && ` · ${receipt.issues.length} flagged`}
                </span>
                <span className="justify-self-end">
                  <StatusBadge status={receipt.status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

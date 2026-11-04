import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { backendFetch } from "../../lib/backend";
import type { ReceiptDetail } from "../../lib/receipts";
import Notice from "../../ui/notice";
import ReceiptCard from "../../ui/receipt-card";
import ReceiptPhoto from "../../ui/receipt-photo";

export const metadata: Metadata = { title: "Receipt" };

export default async function ReceiptPage({ params }: PageProps<"/receipts/[id]">) {
  const { id } = await params;
  const response = await backendFetch(`/receipts/${encodeURIComponent(id)}`);
  // 422 means the ID isn't even a valid UUID, so no receipt can have it
  if (response.status === 404 || response.status === 422) notFound();

  return (
    <div className="mx-auto max-w-6xl">
      <Link href="/receipts" className="text-sm text-muted underline underline-offset-4 hover:text-ink">
        ← Saved receipts
      </Link>
      {response.ok ? (
        <ReceiptView detail={await response.json()} />
      ) : (
        <div className="mt-4">
          <Notice title="Couldn't load this receipt" message="Try again in a minute." />
        </div>
      )}
    </div>
  );
}

function ReceiptView({ detail }: { detail: ReceiptDetail }) {
  return (
    <div className="mt-4 grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <ReceiptPhoto receiptId={detail.id} alt={`Photo of the ${detail.receipt.merchant ?? "unknown store"} receipt`} />
      <ReceiptCard receipt={detail.receipt} issues={detail.issues} status={detail.status} />
    </div>
  );
}

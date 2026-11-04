import { formatDate, formatMoney, STATUS_LABELS, type LineItem, type Receipt } from "../lib/receipts";

// No hooks, so both the upload page (client) and the saved receipt page (server) can render it

export function StatusBadge({ status }: { status: string }) {
  const color = status === "approved" ? "border-ok text-ok" : "border-warn text-warn";
  return (
    <span className={`inline-block border px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${color}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// The small print under an item: its code, and the math when there's more than one
function itemDetails(item: LineItem) {
  const quantity = Number(item.quantity);
  const parts = item.item_code ? [item.item_code] : [];
  if (quantity !== 1) {
    parts.push(item.unit_price === null ? `Qty ${quantity}` : `${quantity} × ${formatMoney(item.unit_price)}`);
  }
  return parts.join(" · ");
}

export default function ReceiptCard({ receipt, issues, status }: { receipt: Receipt; issues: string[]; status?: string }) {
  return (
    <article className="border border-ink bg-panel">
      <header className="flex items-start justify-between gap-4 border-b border-ink p-4 sm:p-5">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold uppercase tracking-wide break-words">{receipt.merchant ?? "Unknown store"}</h2>
          <p className="text-sm text-muted">{formatDate(receipt.purchase_date)}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <p className="font-mono text-2xl tabular-nums">{formatMoney(receipt.total)}</p>
          {status && <StatusBadge status={status} />}
        </div>
      </header>

      {issues.length > 0 ? (
        <div className="border-b border-ink bg-warn-bg px-4 py-3 sm:px-5">
          <p className="text-sm font-semibold text-warn">Needs review</p>
          <ul className="mt-1 list-[square] space-y-0.5 pl-5 text-sm">
            {issues.map((issue, index) => (
              <li key={index}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="border-b border-ink bg-ok-bg px-4 py-3 text-sm font-semibold text-ok sm:px-5">All checks passed</p>
      )}

      {receipt.items.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-muted">
              <th className="py-2 pl-4 font-medium sm:pl-5">Item</th>
              <th className="py-2 pr-4 text-right font-medium sm:pr-5">Amount</th>
            </tr>
          </thead>
          <tbody>
            {receipt.items.map((item, index) => {
              const details = itemDetails(item);
              return (
                <tr key={index} className="border-b border-line last:border-b-0">
                  <td className="py-2.5 pl-4 pr-3 align-top sm:pl-5">
                    <p className="break-words">{item.raw_text}</p>
                    {details && <p className="font-mono text-xs break-all text-muted">{details}</p>}
                  </td>
                  <td className="py-2.5 pr-4 text-right align-top font-mono tabular-nums sm:pr-5">
                    {formatMoney(item.line_total)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      <dl className="border-t border-ink px-4 py-3 text-sm sm:px-5">
        {(["subtotal", "tax", "tip"] as const).map((field) => (
          <div key={field} className="flex justify-between py-0.5">
            <dt className="capitalize text-muted">{field}</dt>
            <dd className="font-mono tabular-nums">{formatMoney(receipt[field])}</dd>
          </div>
        ))}
        <div className="mt-2 flex justify-between border-t border-line pt-2 font-semibold">
          <dt>Total</dt>
          <dd className="font-mono tabular-nums">{formatMoney(receipt.total)}</dd>
        </div>
      </dl>
    </article>
  );
}

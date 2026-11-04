import Link from "next/link";
import Notice, { buttonClass } from "../../ui/notice";

export default function ReceiptNotFound() {
  return (
    <div className="mx-auto max-w-3xl">
      <Notice title="Receipt not found" message="The link may be wrong, or the receipt was deleted.">
        <Link href="/receipts" className={buttonClass}>Back to saved receipts</Link>
      </Notice>
    </div>
  );
}

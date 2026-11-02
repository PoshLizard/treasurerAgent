import Link from "next/link";
import ReceiptUpload from "../ui/receipt-upload";

export default function Receipts() {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold mb-4">Receipts</h1>
      <Link href="/" className="block mb-6 text-blue-600 underline">
        Back to chat
      </Link>
      <ReceiptUpload />
    </main>
  );
}

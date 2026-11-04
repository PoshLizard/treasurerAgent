import type { Metadata } from "next";
import PageHeader from "./ui/page-header";
import ReceiptUpload from "./ui/receipt-upload";

export const metadata: Metadata = { title: "Process a receipt" };

export default function ProcessReceiptPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Process a receipt"
        description="Upload a photo. Gemini reads it, the math is checked in code, and the receipt is saved with its photo for review."
      />
      <ReceiptUpload />
    </div>
  );
}

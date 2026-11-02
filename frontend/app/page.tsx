import Link from "next/link";
import ChatBox from "./ui/chat-box";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold mb-4">Treasurer Agent Chat</h1>
      <Link href="/receipts" className="block text-blue-600 underline">
        Process a receipt
      </Link>
      <ChatBox />
    </main>

  );
}

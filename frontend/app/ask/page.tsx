import type { Metadata } from "next";
import ChatBox from "../ui/chat-box";
import PageHeader from "../ui/page-header";

export const metadata: Metadata = { title: "Ask a question" };

export default function AskPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Ask a question"
        description="Research fundraising ideas, grants and conference funding. Answers only cite pages the agent actually opened."
      />
      <ChatBox />
    </div>
  );
}

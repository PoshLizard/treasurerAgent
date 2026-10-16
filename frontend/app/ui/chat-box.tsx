"use client";
import { useState } from "react";

type Link = { label: string; url: string };
type Answer = { summary: string; action_links?: Link[]; sources: string[] };

// URLs come from model output, so only make http(s) links clickable (never javascript: etc.)
const isWebUrl = (url: string) => /^https?:\/\//i.test(url);

function ExternalLink({ url, label }: { url: string; label?: string }) {
  if (!isWebUrl(url)) return <span>{label ?? url}</span>;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 underline break-all"
    >
      {label ?? url}
    </a>
  );
}

export default function ChatBox() {
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  async function sendMessage() {
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to fetch answer");
      }
      setAnswer(data);
    } catch (error) {
      setError("Couldn't reach server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage();
        }}
      >
        <input
          type="text"
          placeholder="Ask a question..."
          className="w-full p-4 border border-gray-300 rounded-lg"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        ></input>
        <button
          className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg"
          type="submit"
          disabled={loading}
        >
          Send
        </button>
      </form>

      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">{error}</p>}
      {answer && (
        <div className="mt-4 p-4 rounded-lg">
          <p className="whitespace-pre-line">{answer.summary}</p>
          {/* Checked first so an older backend without action_links doesn't crash the page mid-deploy */}
          {answer.action_links && answer.action_links.length > 0 && (
            <div className="mt-4">
              <p className="font-bold">Next steps:</p>
              <ul className="list-disc pl-5">
                {answer.action_links.map((link, index) => (
                  <li key={index}>
                    <ExternalLink url={link.url} label={link.label} />
                  </li>
                ))}
              </ul>
            </div>
          )}
          {answer.sources.length > 0 && (
            <div className="mt-4">
              <p className="font-bold">Sources:</p>
              <ul className="list-disc pl-5">
                {answer.sources.map((source, index) => (
                  <li key={index}>
                    <ExternalLink url={source} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

"use client";
import { useState } from "react";
import { SquaresLoader } from "./loaders";
import { buttonClass } from "./notice";
import { useToast } from "./toast";

type Link = { label: string; url: string };
type Answer = { summary: string; action_links?: Link[]; sources: string[] };

// URLs come from model output, so only make http(s) links clickable (never javascript: etc.)
const isWebUrl = (url: string) => /^https?:\/\//i.test(url);

function ExternalLink({ url, label }: { url: string; label?: string }) {
  if (!isWebUrl(url)) return <span>{label ?? url}</span>;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="break-all underline underline-offset-4 hover:no-underline">
      {label ?? url}
    </a>
  );
}

export default function ChatBox() {
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const showToast = useToast();

  async function sendMessage() {
    setLoading(true);
    setAnswer(null);
    setQuestion(message);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        showToast(typeof data?.detail === "string" ? data.detail : "Couldn't get an answer. Try again.");
        return;
      }
      setAnswer(data);
    } catch {
      showToast("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage();
        }}
      >
        <input
          type="text"
          aria-label="Question"
          placeholder="e.g. Restaurant fundraisers near campus"
          className="min-w-0 flex-1 border border-ink bg-panel px-3 py-2 placeholder:text-muted"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button className={buttonClass} type="submit" disabled={loading || !message.trim()}>
          Ask
        </button>
      </form>

      {(loading || answer) && (
        <article className="border border-ink bg-panel">
          <p className="border-b border-ink px-4 py-3 text-sm font-medium sm:px-5">{question}</p>
          <div className="p-4 sm:p-5">
            {loading && <SquaresLoader label="Researching. This can take a minute." />}
            {answer && (
              <>
                <p className="whitespace-pre-line leading-relaxed">{answer.summary}</p>
                {/* Checked first so an older backend without action_links doesn't crash the page mid-deploy */}
                {answer.action_links && answer.action_links.length > 0 && (
                  <div className="mt-5 border-t border-line pt-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">Next steps</p>
                    <ul className="mt-2 list-[square] space-y-1 pl-5">
                      {answer.action_links.map((link, index) => (
                        <li key={index}>
                          <ExternalLink url={link.url} label={link.label} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {answer.sources.length > 0 && (
                  <div className="mt-5 border-t border-line pt-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted">Sources</p>
                    <ul className="mt-2 list-[square] space-y-1 pl-5 text-sm text-muted">
                      {answer.sources.map((source, index) => (
                        <li key={index}>
                          <ExternalLink url={source} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        </article>
      )}
    </div>
  );
}

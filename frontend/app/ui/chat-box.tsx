"use client";
import { useState } from "react";
import { SquaresLoader } from "./loaders";
import { buttonClass } from "./notice";
import { useToast } from "./toast";

type Link = { label: string; url: string };
type Answer = { summary: string; action_links?: Link[]; sources: string[] };
type AgentEvent =
  | { type: "thought"; text: string }
  | { type: "step"; text: string }
  | { type: "answer"; answer: Answer }
  | { type: "error"; detail: string };

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

// Gemini writes each thought as "**Heading** text", so show the headings in bold
function Thoughts({ text }: { text: string }) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">
      {parts.map((part, index) => (index % 2 ? <strong key={index} className="text-ink">{part}</strong> : part))}
    </p>
  );
}

function Activity({ steps, thoughts, live }: { steps: string[]; thoughts: string; live: boolean }) {
  return (
    <div className="space-y-3">
      {steps.length > 0 && (
        <ol className="space-y-1.5 text-sm">
          {steps.map((step, index) => (
            <li key={index} className="flex items-start gap-2.5">
              <span
                aria-hidden="true"
                className={`mt-1.5 size-2 shrink-0 bg-ink ${live && index === steps.length - 1 ? "motion-safe:animate-blink" : ""}`}
              />
              <span className="break-all">{step}</span>
            </li>
          ))}
        </ol>
      )}
      {thoughts && (
        <div className="border-l-2 border-line-strong pl-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted">Thinking</p>
          <Thoughts text={thoughts} />
        </div>
      )}
    </div>
  );
}

// Splits a Server-Sent Events stream into its events: "data: {json}" lines, each followed by a blank line
async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<AgentEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true }); // stream: a character can be split across chunks
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? ""; // the last piece may be half an event, so wait for the rest
    for (const chunk of chunks) {
      if (chunk.startsWith("data: ")) yield JSON.parse(chunk.slice("data: ".length));
    }
  }
}

export default function ChatBox() {
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [steps, setSteps] = useState<string[]>([]);
  const [thoughts, setThoughts] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const showToast = useToast();

  async function sendMessage() {
    setLoading(true);
    setAnswer(null);
    setSteps([]);
    setThoughts("");
    setQuestion(message);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });
      if (!response.ok || !response.body) {
        const data = await response.json().catch(() => null);
        showToast(typeof data?.detail === "string" ? data.detail : "Couldn't get an answer. Try again.");
        return;
      }

      let finished = false;
      for await (const event of readEvents(response.body)) {
        if (event.type === "thought") setThoughts((current) => current + event.text);
        else if (event.type === "step") setSteps((current) => [...current, event.text]);
        else if (event.type === "answer") setAnswer(event.answer);
        else showToast(event.detail);
        finished ||= event.type === "answer" || event.type === "error";
      }
      if (!finished) showToast("The answer was cut off. Try asking again.");
    } catch {
      showToast("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  const hasActivity = steps.length > 0 || thoughts !== "";

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

      {(loading || answer || hasActivity) && (
        <article className="border border-ink bg-panel">
          <p className="border-b border-ink px-4 py-3 text-sm font-medium sm:px-5">{question}</p>
          <div className="space-y-4 p-4 sm:p-5">
            {loading && (
              <>
                {hasActivity ? <Activity steps={steps} thoughts={thoughts} live /> : <SquaresLoader label="Starting research" />}
                {hasActivity && <SquaresLoader label="Researching" />}
              </>
            )}
            {answer && (
              <>
                <p className="whitespace-pre-line leading-relaxed">{answer.summary}</p>
                {/* Checked first so an older backend without action_links doesn't crash the page mid-deploy */}
                {answer.action_links && answer.action_links.length > 0 && (
                  <div className="border-t border-line pt-4">
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
                  <div className="border-t border-line pt-4">
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
            {!loading && hasActivity && (
              <details className="border-t border-line pt-4">
                <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-muted">
                  How it got this answer
                </summary>
                <div className="mt-3">
                  <Activity steps={steps} thoughts={thoughts} live={false} />
                </div>
              </details>
            )}
          </div>
        </article>
      )}
    </div>
  );
}

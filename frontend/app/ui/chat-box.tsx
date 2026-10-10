"use client";
import { useState } from "react";

type Answer = { summary: string; sources: string[] };

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
          <p>{answer.summary}</p>
          {answer.sources.length > 0 && (
            <div className="mt-2">
              <p className="font-bold">Sources:</p>
              <ul>
                {answer.sources.map((source, index) => (
                  <li key={index}>{source}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { streamFromBackend } from "../../lib/backend";

// Streams the agent's thoughts and steps to the page as they happen, then its answer
export async function POST(request: Request) {
    return streamFromBackend("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await request.text()
    });
}

import { forwardToBackend } from "../../lib/backend";

export async function POST(request: Request) {
    return forwardToBackend("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await request.text()
    });
}

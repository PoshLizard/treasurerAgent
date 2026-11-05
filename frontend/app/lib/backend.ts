// Fails the build if a Client Component imports this, so API_SECRET can never reach the browser
import "server-only";

type BackendRequest = { method?: string; headers?: Record<string, string>; body?: BodyInit };

export function backendFetch(path: string, init: BackendRequest = {}) {
  return fetch(`${process.env.BACKEND_URL}${path}`, {
    ...init,
    headers: { ...init.headers, "X-API-Key": process.env.API_SECRET || "" },
  });
}

// For route handlers: passes the backend's response through, error messages included
export async function forwardToBackend(path: string, init: BackendRequest = {}) {
  let response: Response;
  try {
    response = await backendFetch(path, init);
  } catch {
    return Response.json({ detail: "Couldn't reach the server. Try again in a minute." }, { status: 502 });
  }
  // A 204 (a successful delete) must have no body at all, not even an empty one
  return new Response(response.status === 204 ? null : await response.text(), {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "text/plain" },
  });
}

// For streamed answers: hands each backend event to the browser as it arrives, instead of
// waiting for the whole response the way forwardToBackend does
export async function streamFromBackend(path: string, init: BackendRequest = {}) {
  let response: Response;
  try {
    response = await backendFetch(path, init);
  } catch {
    return Response.json({ detail: "Couldn't reach the server. Try again in a minute." }, { status: 502 });
  }
  if (!response.ok || !response.body) {
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") ?? "text/plain" },
    });
  }
  return new Response(response.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no" },
  });
}

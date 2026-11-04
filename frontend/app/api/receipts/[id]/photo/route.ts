import { backendFetch } from "../../../../lib/backend";

// The page points <img> here instead of at Supabase. Every request gets a fresh, short-lived
// link, so the photo still works however long the page has been open.
export async function GET(_request: Request, { params }: RouteContext<"/api/receipts/[id]/photo">) {
    const { id } = await params;
    const response = await backendFetch(`/receipts/${encodeURIComponent(id)}/photo`).catch(() => null);
    if (!response?.ok) {
        // 422 means the ID isn't even a valid UUID, so no receipt can have it
        const notFound = response?.status === 404 || response?.status === 422;
        return new Response(null, { status: notFound ? 404 : 502 });
    }
    const { url } = await response.json();
    // no-store: a cached redirect would send the browser to a link that has since expired
    return new Response(null, { status: 307, headers: { Location: url, "Cache-Control": "no-store" } });
}

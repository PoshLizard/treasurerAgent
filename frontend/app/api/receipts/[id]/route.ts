import { forwardToBackend } from "../../../lib/backend";

export async function PUT(request: Request, { params }: RouteContext<"/api/receipts/[id]">) {
    const { id } = await params;
    return forwardToBackend(`/receipts/${encodeURIComponent(id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: await request.text()
    });
}

export async function DELETE(_request: Request, { params }: RouteContext<"/api/receipts/[id]">) {
    const { id } = await params;
    return forwardToBackend(`/receipts/${encodeURIComponent(id)}`, { method: "DELETE" });
}

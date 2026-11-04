import { forwardToBackend } from "../../lib/backend";

export async function POST(request: Request) {
    // No Content-Type header: fetch sets it, including the boundary that separates the form's parts
    return forwardToBackend("/receipts", { method: "POST", body: await request.formData() });
}

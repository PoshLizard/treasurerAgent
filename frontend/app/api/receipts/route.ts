export async function GET() {
    const response = await fetch(`${process.env.BACKEND_URL}/receipts`, {
        headers: {
            "X-API-Key": process.env.API_SECRET || ""
        }
    });
    const data = await response.json();
    return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
            "Content-Type": "application/json"
        }
    });
}

export async function POST(request: Request) {
    // No Content-Type header: fetch sets it, including the boundary that separates the form's parts
    const response = await fetch(`${process.env.BACKEND_URL}/receipts`, {
        method: "POST",
        headers: {
            "X-API-Key": process.env.API_SECRET || ""
        },
        body: await request.formData()
    });
    const data = await response.json();
    return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
            "Content-Type": "application/json"
        }
    });
}

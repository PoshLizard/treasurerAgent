export async function POST(request: Request) {
    const body = await request.json();
    const response = await fetch(`${process.env.BACKEND_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });
    const data = await response.json();
    return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
            "Content-Type": "application/json"
        }
    });
}
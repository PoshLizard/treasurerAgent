import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function safeEqual(a: string, b: string): boolean {
  const bufferA = Buffer.from(a);
  const bufferB = Buffer.from(b);
  return bufferA.length === bufferB.length && timingSafeEqual(bufferA, bufferB);
}

export function proxy(request: NextRequest) {
  const expectedUser = process.env.BASIC_AUTH_USER;
  const expectedPassword = process.env.BASIC_AUTH_PASSWORD;
  const header = request.headers.get("authorization");

  if (expectedUser && expectedPassword && header?.startsWith("Basic ")) {
    const decoded = atob(header.slice("Basic ".length));
    const separator = decoded.indexOf(":");
    const user = decoded.slice(0, separator);
    const password = decoded.slice(separator + 1);

    if (safeEqual(user, expectedUser) && safeEqual(password, expectedPassword)) {
      return NextResponse.next();
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Treasurer Agent"' },
  });
}

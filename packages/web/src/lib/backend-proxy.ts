import { auth } from "@/auth";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const BACKEND_SECRET = process.env.BACKEND_SECRET || "";

/**
 * Forward an authenticated request to the Python backend.
 *
 * 1. Validates the NextAuth session
 * 2. Attaches X-Backend-Secret and X-User-Id headers
 * 3. Proxies the request to BACKEND_URL
 */
export async function proxyToBackend(
  request: NextRequest,
  backendPath: string,
): Promise<NextResponse> {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${BACKEND_URL}${backendPath}${searchParams ? `?${searchParams}` : ""}`;

    const headers: HeadersInit = {
      "X-Backend-Secret": BACKEND_SECRET,
      "X-User-Id": session.user.id,
    };

    // Pass user profile for auto-creation on first login
    if (session.user.email) {
      headers["X-User-Email"] = session.user.email;
    }
    if (session.user.name) {
      headers["X-User-Name"] = session.user.name;
    }
    if (session.user.image) {
      headers["X-User-Image"] = session.user.image;
    }

    // Preserve Content-Type for requests with a body
    const contentType = request.headers.get("content-type");
    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    const hasBody = !["GET", "HEAD"].includes(request.method);

    const res = await fetch(url, {
      method: request.method,
      headers,
      body: hasBody ? await request.text() : undefined,
    });

    // 204 No Content — return empty response
    if (res.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
    });
  } catch (error) {
    console.error(`[BFF Proxy] ${backendPath} failed:`, error);
    const message =
      error instanceof Error ? error.message : "Internal proxy error";
    return NextResponse.json(
      { error: "Backend proxy error", detail: message },
      { status: 502 },
    );
  }
}

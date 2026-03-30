import { auth } from "@/auth";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const BACKEND_SECRET = process.env.BACKEND_SECRET || "";

/**
 * CLI authentication callback.
 *
 * Flow:
 * 1. CLI runs `rewind login` -> opens browser to /api/auth/cli?port=PORT
 * 2. This route checks the NextAuth session
 * 3. If not logged in, redirects to /login with callbackUrl back here
 * 4. If logged in, calls the backend to create an API key
 * 5. Redirects to http://localhost:PORT?key=rw_... for the CLI to capture
 */
export async function GET(request: NextRequest) {
  const port = request.nextUrl.searchParams.get("port");
  const deviceName = request.nextUrl.searchParams.get("device") || "cli";

  if (!port) {
    return NextResponse.json(
      { error: "Missing 'port' query parameter" },
      { status: 400 },
    );
  }

  const session = await auth();

  if (!session?.user?.id) {
    // Redirect to login, then back to this endpoint
    const callbackUrl = new URL(request.url);
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", callbackUrl.toString());
    return NextResponse.redirect(loginUrl);
  }

  // Create API key via backend
  // NOTE: Backend needs a POST /api/keys endpoint that accepts
  // { device_name } and returns { key, id, created_at }.
  // This endpoint is authenticated via BFF headers.
  try {
    const res = await fetch(`${BACKEND_URL}/api/keys`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Backend-Secret": BACKEND_SECRET,
        "X-User-Id": session.user.id,
        ...(session.user.email && { "X-User-Email": session.user.email }),
        ...(session.user.name && { "X-User-Name": session.user.name }),
        ...(session.user.image && { "X-User-Image": session.user.image }),
      },
      body: JSON.stringify({ device_name: deviceName }),
    });

    if (!res.ok) {
      const body = await res.text();
      return NextResponse.json(
        { error: "Failed to create API key", detail: body },
        { status: res.status },
      );
    }

    const { key } = (await res.json()) as { key: string };

    // Redirect to CLI's local server with the key
    return NextResponse.redirect(`http://localhost:${port}?key=${key}`);
  } catch {
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 502 },
    );
  }
}

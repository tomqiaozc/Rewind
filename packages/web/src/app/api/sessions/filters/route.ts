import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export function GET(req: NextRequest) {
  return proxyToBackend(req, "/api/sessions/filters");
}

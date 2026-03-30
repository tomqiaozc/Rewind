import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export function POST(req: NextRequest) {
  return proxyToBackend(req, "/api/keys");
}

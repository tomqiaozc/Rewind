import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyToBackend(req, `/api/tags/${id}`));
}

export function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyToBackend(req, `/api/tags/${id}`));
}

import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyToBackend(req, `/api/sessions/${id}/trash`));
}

export function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyToBackend(req, `/api/sessions/${id}/trash`));
}

import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; tagId: string }> },
) {
  return params.then(({ id, tagId }) =>
    proxyToBackend(req, `/api/sessions/${id}/tags/${tagId}`),
  );
}

export function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string; tagId: string }> },
) {
  return params.then(({ id, tagId }) =>
    proxyToBackend(req, `/api/sessions/${id}/tags/${tagId}`),
  );
}

import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyToBackend(req, `/api/keys/${id}`));
}

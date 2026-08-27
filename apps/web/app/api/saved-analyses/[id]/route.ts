import { problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";

export const dynamic = "force-dynamic";

const offline = () =>
  problem(501, "Not implemented", "Saved analyses are not wired to a database yet.");

/** PATCH /api/saved-analyses/:id — update a saved analysis (e.g. pause its schedule). */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyOr(request, `/v1/saved-analyses/${encodeURIComponent(id)}`, offline);
}

/** DELETE /api/saved-analyses/:id */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyOr(request, `/v1/saved-analyses/${encodeURIComponent(id)}`, offline);
}

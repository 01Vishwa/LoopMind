import { problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";

export const dynamic = "force-dynamic";

/**
 * POST /api/saved-analyses/:id/run — run a saved analysis now.
 *
 * Proxies `POST {API_URL}/v1/saved-analyses/:id/run`; offline it returns 501.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyOr(request, `/v1/saved-analyses/${encodeURIComponent(id)}/run`, () =>
    problem(501, "Not implemented", "Saved analyses are not wired to the orchestrator yet."),
  );
}

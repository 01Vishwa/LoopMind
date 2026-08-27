import { problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";

export const dynamic = "force-dynamic";

/**
 * POST /api/runs/:runId/retry — re-run a failed run with the same inputs.
 *
 * Proxies `POST {API_URL}/v1/runs/:runId/retry`; offline it returns 501.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  return proxyOr(request, `/v1/runs/${encodeURIComponent(runId)}/retry`, () =>
    problem(501, "Not implemented", "Retry is not wired to the orchestrator yet."),
  );
}

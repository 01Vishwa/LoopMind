import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { RunDetail } from "@/lib/data/runDetail";

export const dynamic = "force-dynamic";

/**
 * GET /api/runs/:runId — everything the run detail page renders.
 *
 * Proxies `GET {API_URL}/v1/runs/:runId`. Offline it returns a fully-shaped
 * zero state so the page renders instead of throwing on undefined.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  return proxyOr(request, `/v1/runs/${encodeURIComponent(runId)}`, () =>
    json<RunDetail>({
      runId,
      workspaceId: "",
      workspaceName: "",
      query: "",
      status: {
        phase: "connecting",
        round: 0,
        maxRounds: 0,
        elapsedMs: 0,
        costUsd: 0,
        costLimitUsd: 0,
      },
      steps: [],
      backtracks: [],
      roundLogs: [],
      verdict: null,
      verification: null,
    }),
  );
}

import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { RunProvenance } from "@/lib/data/provenance";

export const dynamic = "force-dynamic";

/**
 * GET /api/runs/:runId/provenance — the reproducibility record for a run.
 *
 * Proxies `GET {API_URL}/v1/runs/:runId/provenance`; offline it returns an
 * empty record.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  return proxyOr(request, `/v1/runs/${encodeURIComponent(runId)}/provenance`, () =>
    json<RunProvenance>({
      query: "",
      files: [],
      finalScript: "",
      answer: "",
      rounds: [],
      models: [],
      metadata: {
        runId,
        startedAt: "",
        finishedAt: "",
        totalCostUsd: 0,
        totalTokens: 0,
        traceId: "",
      },
    }),
  );
}

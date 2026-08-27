import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { RunReport } from "@/lib/data/report";

export const dynamic = "force-dynamic";

/**
 * GET /api/runs/:runId/report — the cited report from a deep-research run.
 *
 * Proxies `GET {API_URL}/v1/runs/:runId/report`; offline it returns an empty
 * report.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  return proxyOr(request, `/v1/runs/${encodeURIComponent(runId)}/report`, () =>
    json<RunReport>({ runId, markdown: "", subQuestions: [] }),
  );
}

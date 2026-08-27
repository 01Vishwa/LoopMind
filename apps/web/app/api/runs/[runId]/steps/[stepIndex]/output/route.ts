import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { StepOutput } from "@/lib/data/runDetail";

export const dynamic = "force-dynamic";

/**
 * GET /api/runs/:runId/steps/:stepIndex/output — execution output for a step.
 *
 * Proxies `GET {API_URL}/v1/runs/:runId/steps/:stepIndex/output`; offline it
 * returns an empty payload.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string; stepIndex: string }> },
) {
  const { runId, stepIndex } = await params;
  return proxyOr(
    request,
    `/v1/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepIndex)}/output`,
    () => json<StepOutput>({ columns: [], rows: [], raw: "" }),
  );
}

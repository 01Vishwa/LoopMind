import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { StepCode } from "@/lib/data/runDetail";

export const dynamic = "force-dynamic";

/**
 * GET /api/runs/:runId/steps/:stepIndex/code — generated code for one step.
 *
 * Proxies `GET {API_URL}/v1/runs/:runId/steps/:stepIndex/code`; offline it
 * returns an empty payload.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string; stepIndex: string }> },
) {
  const { runId, stepIndex } = await params;
  return proxyOr(
    request,
    `/v1/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepIndex)}/code`,
    () => json<StepCode>({ source: "", language: "", fileExtension: "" }),
  );
}

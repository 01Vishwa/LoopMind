import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { UsageBreakdownSection } from "@/lib/data/usage";

export const dynamic = "force-dynamic";

/**
 * GET /api/usage/periods/:periodId/breakdown — spend split by model, agent,
 * and workspace for one period.
 *
 * Proxies `GET {API_URL}/v1/usage/periods/:periodId/breakdown`; offline it
 * returns an empty list.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ periodId: string }> },
) {
  const { periodId } = await params;
  return proxyOr(
    request,
    `/v1/usage/periods/${encodeURIComponent(periodId)}/breakdown`,
    () => json<UsageBreakdownSection[]>([]),
  );
}

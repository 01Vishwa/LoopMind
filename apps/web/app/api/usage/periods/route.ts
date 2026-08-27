import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { UsagePeriod } from "@/lib/data/usage";

export const dynamic = "force-dynamic";

/**
 * GET /api/usage/periods — billing periods, newest first.
 *
 * Proxies `GET {API_URL}/v1/usage/periods`; offline it returns an empty list.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/usage/periods", () => json<UsagePeriod[]>([]));
}

import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { SavedAnalysis } from "@/lib/data/types";

export const dynamic = "force-dynamic";

/**
 * GET /api/saved-analyses — every saved analysis for the caller.
 *
 * Proxies `GET {API_URL}/v1/saved-analyses`; offline it returns an empty list.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/saved-analyses", () => json<SavedAnalysis[]>([]));
}

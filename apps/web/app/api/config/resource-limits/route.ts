import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import { DEFAULT_RESOURCE_LIMITS, type ResourceLimits } from "@/lib/config/resourceLimits";

export const dynamic = "force-dynamic";

/**
 * GET /api/config/resource-limits — round and cost ceilings for a new run.
 *
 * Proxies `GET {API_URL}/v1/config/resource-limits`; offline it serves the
 * built-in defaults.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/config/resource-limits", () =>
    json<ResourceLimits>(DEFAULT_RESOURCE_LIMITS),
  );
}

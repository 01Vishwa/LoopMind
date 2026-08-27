import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { ModelOption } from "@/components/settings/ModelSelector";

export const dynamic = "force-dynamic";

/**
 * GET /api/settings/providers/:providerId/models — models the tenant may pick.
 *
 * Proxies `GET {API_URL}/v1/settings/providers/:providerId/models`; offline it
 * returns an empty list (which disables the Agent Defaults selectors).
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ providerId: string }> },
) {
  const { providerId } = await params;
  return proxyOr(
    request,
    `/v1/settings/providers/${encodeURIComponent(providerId)}/models`,
    () => json<ModelOption[]>([]),
  );
}

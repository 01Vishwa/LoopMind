import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { SuggestedQuestion } from "@/lib/data/types";

export const dynamic = "force-dynamic";

/**
 * GET /api/workspaces/:workspaceId/suggested-questions — starter prompts.
 *
 * Proxies `GET {API_URL}/v1/workspaces/:workspaceId/suggested-questions`;
 * offline it returns an empty list.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await params;
  return proxyOr(
    request,
    `/v1/workspaces/${encodeURIComponent(workspaceId)}/suggested-questions`,
    () => json<SuggestedQuestion[]>([]),
  );
}

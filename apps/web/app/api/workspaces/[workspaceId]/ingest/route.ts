import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { WorkspaceFile } from "@/lib/schemas/runSchemas";

export const dynamic = "force-dynamic";

/**
 * POST /api/workspaces/:workspaceId/ingest — analyse every pending file.
 *
 * Proxies `POST {API_URL}/v1/workspaces/:workspaceId/ingest`; offline it
 * returns an empty updated file list.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await params;
  return proxyOr(request, `/v1/workspaces/${encodeURIComponent(workspaceId)}/ingest`, () =>
    json<WorkspaceFile[]>([]),
  );
}

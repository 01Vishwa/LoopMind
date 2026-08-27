import { problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";

export const dynamic = "force-dynamic";

/**
 * GET /api/workspaces/:workspaceId — a single workspace.
 *
 * Proxies `GET {API_URL}/v1/workspaces/:workspaceId`; offline every id is
 * unknown (404), the honest answer for an empty store.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await params;
  return proxyOr(request, `/v1/workspaces/${encodeURIComponent(workspaceId)}`, () =>
    problem(404, "Workspace not found", `No workspace with id "${workspaceId}".`),
  );
}

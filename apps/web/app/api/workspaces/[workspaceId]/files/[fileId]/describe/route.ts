import { problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";

export const dynamic = "force-dynamic";

/**
 * POST /api/workspaces/:workspaceId/files/:fileId/describe — re-run the Data
 * File Analyzer on one file.
 *
 * Proxies `POST {API_URL}/v1/workspaces/:workspaceId/files/:fileId/describe`;
 * offline it returns 501.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string; fileId: string }> },
) {
  const { workspaceId, fileId } = await params;
  return proxyOr(
    request,
    `/v1/workspaces/${encodeURIComponent(workspaceId)}/files/${encodeURIComponent(fileId)}/describe`,
    () => problem(501, "Not implemented", "File analysis is not wired to the analyzer yet."),
  );
}

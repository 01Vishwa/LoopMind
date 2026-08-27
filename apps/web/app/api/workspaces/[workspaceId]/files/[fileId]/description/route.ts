import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { FileDescription } from "@/lib/data/fileDescriptions";

export const dynamic = "force-dynamic";

/**
 * GET /api/workspaces/:workspaceId/files/:fileId/description — what the Data
 * File Analyzer learned about one file.
 *
 * Proxies `GET {API_URL}/v1/workspaces/:workspaceId/files/:fileId/description`;
 * offline it returns an empty description.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string; fileId: string }> },
) {
  const { workspaceId, fileId } = await params;
  return proxyOr(
    request,
    `/v1/workspaces/${encodeURIComponent(workspaceId)}/files/${encodeURIComponent(fileId)}/description`,
    () =>
      json<FileDescription>({
        schema: [],
        analyzerScript: "",
        scriptStatus: "verified",
        rawOutput: "",
      }),
  );
}

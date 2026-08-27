import { json, problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { WorkspaceFile } from "@/lib/schemas/runSchemas";

export const dynamic = "force-dynamic";

/**
 * GET /api/workspaces/:workspaceId/files — files uploaded to a workspace.
 *
 * Proxies `GET {API_URL}/v1/workspaces/:workspaceId/files`; offline it returns
 * an empty list.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await params;
  return proxyOr(request, `/v1/workspaces/${encodeURIComponent(workspaceId)}/files`, () =>
    json<WorkspaceFile[]>([]),
  );
}

/** POST /api/workspaces/:workspaceId/files — upload one file (multipart). */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ workspaceId: string }> },
) {
  const { workspaceId } = await params;

  const form = await request.clone().formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof File)) {
    return problem(422, "Invalid upload", 'A file part named "file" is required.');
  }

  return proxyOr(request, `/v1/workspaces/${encodeURIComponent(workspaceId)}/files`, () =>
    problem(501, "Not implemented", "File uploads are not wired to storage yet."),
  );
}

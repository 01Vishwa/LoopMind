import { json, problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { Workspace } from "@/lib/schemas/runSchemas";

export const dynamic = "force-dynamic";

/**
 * GET /api/workspaces — every workspace visible to the caller.
 *
 * Proxies `GET {API_URL}/v1/workspaces`; offline it returns an empty list.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/workspaces", () => json<Workspace[]>([]));
}

/** POST /api/workspaces — create a workspace. */
export async function POST(request: Request) {
  const body = (await request.clone().json().catch(() => null)) as
    | { name?: string; description?: string }
    | null;

  if (!body?.name?.trim()) {
    return problem(422, "Invalid workspace", "A workspace name is required.");
  }

  return proxyOr(request, "/v1/workspaces", () =>
    problem(501, "Not implemented", "Workspace creation is not wired to a database yet."),
  );
}

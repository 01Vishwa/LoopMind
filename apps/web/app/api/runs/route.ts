import { json, problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { Paginated, RunListItem } from "@/lib/data/types";

export const dynamic = "force-dynamic";

/**
 * GET /api/runs?status=&workspaceId=&q=&limit=&cursor=&sort=&order= — run list.
 *
 * Proxies `GET {API_URL}/v1/runs` (query string forwarded verbatim, so
 * filtering, search, sort, and pagination are all server-side). Offline it
 * returns an empty page.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/runs", () =>
    json<Paginated<RunListItem>>({ items: [], total: 0, showing: 0 }),
  );
}

/** POST /api/runs — start a run. */
export async function POST(request: Request) {
  const body = (await request.clone().json().catch(() => null)) as
    | { workspaceId?: string; query?: string }
    | null;

  if (!body?.workspaceId || !body?.query?.trim()) {
    return problem(422, "Invalid run request", "A workspace and a question are required.");
  }

  return proxyOr(request, "/v1/runs", () =>
    problem(501, "Not implemented", "Run creation is not wired to the orchestrator yet."),
  );
}

import { json, problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { TeamMember } from "@/lib/data/team";

export const dynamic = "force-dynamic";

/**
 * GET /api/team/members — members and outstanding invitations.
 *
 * Proxies `GET {API_URL}/v1/team/members`; offline it returns an empty list.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/team/members", () => json<TeamMember[]>([]));
}

/** POST /api/team/members — invite someone by email. */
export async function POST(request: Request) {
  const body = (await request.clone().json().catch(() => null)) as { email?: string } | null;

  if (!body?.email?.trim()) {
    return problem(422, "Invalid invitation", "An email address is required.");
  }

  return proxyOr(request, "/v1/team/members", () =>
    problem(501, "Not implemented", "Team management is not wired to a database yet."),
  );
}

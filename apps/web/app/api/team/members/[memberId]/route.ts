import { problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";

export const dynamic = "force-dynamic";

const offline = () =>
  problem(501, "Not implemented", "Team management is not wired to a database yet.");

/** PATCH /api/team/members/:memberId — change a member's role. */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ memberId: string }> },
) {
  const { memberId } = await params;
  return proxyOr(request, `/v1/team/members/${encodeURIComponent(memberId)}`, offline);
}

/** DELETE /api/team/members/:memberId — remove a member or revoke an invitation. */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ memberId: string }> },
) {
  const { memberId } = await params;
  return proxyOr(request, `/v1/team/members/${encodeURIComponent(memberId)}`, offline);
}

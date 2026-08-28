import { proxyOr } from "@/app/api/_lib/proxy";
import { json } from "@/app/api/_lib/respond";

export const dynamic = "force-dynamic";

/** POST /api/auth/logout → POST /v1/auth/logout */
export async function POST(request: Request) {
  return proxyOr(request, "/v1/auth/logout", () =>
    // Offline stub — 204 success even without a backend.
    json(null, { status: 204 }),
  );
}

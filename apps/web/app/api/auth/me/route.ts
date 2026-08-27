import { json, problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { CurrentUser } from "@/lib/data/types";

export const dynamic = "force-dynamic";

/**
 * GET /api/auth/me — the authenticated session.
 *
 * Proxies `GET {API_URL}/v1/auth/me` (forwarding the bearer token). Offline it
 * returns a blank viewer so the shell still renders; a real backend returns 401
 * when the token is missing/expired, surfacing the error state in `AuthProvider`.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/auth/me", () =>
    json<CurrentUser>({
      id: "",
      name: "",
      email: "",
      role: "viewer",
      authProvider: "local",
      emailManaged: false,
    }),
  );
}

/** PATCH /api/auth/me — save the editable profile fields. */
export async function PATCH(request: Request) {
  return proxyOr(request, "/v1/auth/me", () =>
    problem(501, "Not implemented", "Profile updates are not wired to a database yet."),
  );
}

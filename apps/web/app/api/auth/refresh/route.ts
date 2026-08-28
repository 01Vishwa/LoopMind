import { proxyOr } from "@/app/api/_lib/proxy";
import { problem } from "@/app/api/_lib/respond";

export const dynamic = "force-dynamic";

/** POST /api/auth/refresh → POST /v1/auth/refresh */
export async function POST(request: Request) {
  return proxyOr(request, "/v1/auth/refresh", () =>
    problem(401, "Unauthorized", "No backend configured — cannot refresh session."),
  );
}

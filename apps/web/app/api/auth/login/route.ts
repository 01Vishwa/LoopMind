import { proxyOr } from "@/app/api/_lib/proxy";
import { problem } from "@/app/api/_lib/respond";

export const dynamic = "force-dynamic";

/** POST /api/auth/login → POST /v1/auth/login */
export async function POST(request: Request) {
  return proxyOr(request, "/v1/auth/login", () =>
    problem(501, "Not implemented", "Backend not configured."),
  );
}

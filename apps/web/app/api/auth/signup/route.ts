import { proxyOr } from "@/app/api/_lib/proxy";
import { problem } from "@/app/api/_lib/respond";

export const dynamic = "force-dynamic";

/** POST /api/auth/signup → POST /v1/auth/signup */
export async function POST(request: Request) {
  return proxyOr(request, "/v1/auth/signup", () =>
    problem(501, "Not implemented", "Backend not configured."),
  );
}

import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import { MODES, type ModeDTO } from "@/lib/config/modes";

export const dynamic = "force-dynamic";

/**
 * GET /api/config/modes — the analysis-mode catalogue.
 *
 * Proxies `GET {API_URL}/v1/config/modes`; offline it serves the built-in
 * catalogue. Icons are omitted (they cannot cross an API boundary) and are
 * resolved client-side from `MODE_ICONS`.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/config/modes", () =>
    json<ModeDTO[]>(MODES.map(({ icon: _icon, ...rest }) => rest)),
  );
}

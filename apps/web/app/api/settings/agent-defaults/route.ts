import { json, problem } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { AgentDefaults, AgentDefaultsSettings } from "@/lib/data/agentDefaults";

export const dynamic = "force-dynamic";

/**
 * VERA's recommended baseline. Serves as both the initial value and the target
 * of "Reset to recommended defaults" until per-tenant rows exist.
 */
const RECOMMENDED: AgentDefaults = {
  maxRounds: 7,
  maxCostUsd: 2.5,
  maxDebugAttempts: 3,
  reasoningModel: "",
  utilityModel: "",
  maxFilesPerWorkspace: 50,
  maxFileSizeMb: 100,
  retrieverTopK: 12,
};

/**
 * GET /api/settings/agent-defaults — saved values, the recommended baseline,
 * and the editable bounds.
 *
 * Proxies `GET {API_URL}/v1/settings/agent-defaults`; offline it serves the
 * built-in recommendation.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/settings/agent-defaults", () =>
    json<AgentDefaultsSettings>({
      values: RECOMMENDED,
      recommended: RECOMMENDED,
      bounds: {
        maxRounds: { min: 1, max: 10 },
        maxCostUsd: { min: 0.1, max: 50, step: 0.1 },
        maxDebugAttempts: { min: 0, max: 10 },
        maxFilesPerWorkspace: { min: 1, max: 500 },
        maxFileSizeMb: { min: 1, max: 500 },
        retrieverTopK: { min: 1, max: 30 },
      },
    }),
  );
}

/** PUT /api/settings/agent-defaults — persist the tenant's overrides. */
export async function PUT(request: Request) {
  return proxyOr(request, "/v1/settings/agent-defaults", () =>
    problem(501, "Not implemented", "Agent defaults are not wired to a database yet."),
  );
}

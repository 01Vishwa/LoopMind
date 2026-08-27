import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import type { ProviderSummary } from "@/lib/data/providers";

export const dynamic = "force-dynamic";

/**
 * GET /api/settings/providers — the model-provider catalogue plus, per provider,
 * whether the tenant has a working key.
 *
 * Proxies `GET {API_URL}/v1/settings/providers`; offline it serves the built-in
 * catalogue with `connected: false`.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/settings/providers", () =>
    json<ProviderSummary[]>([
      {
        id: "openrouter",
        name: "OpenRouter",
        description: "Access 200+ models through a single unified API key.",
        keyPrefix: "sk-or-v1-",
        docsUrl: "https://openrouter.ai/keys",
        icon: "🔀",
        accentColor: "#7C3AED",
        connected: false,
      },
      {
        id: "nvidia",
        name: "NVIDIA NIM",
        description: "Run optimised NVIDIA models — Llama 3.1, Mistral, and more.",
        keyPrefix: "nvapi-",
        docsUrl: "https://build.nvidia.com/nim",
        icon: "⚡",
        accentColor: "#76B900",
        connected: false,
      },
    ]),
  );
}

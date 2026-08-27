import { json } from "@/app/api/_lib/respond";
import { proxyOr } from "@/app/api/_lib/proxy";
import { SUPPORTED_FILE_TYPES, type SupportedFileType } from "@/lib/config/fileTypes";

export const dynamic = "force-dynamic";

/**
 * GET /api/config/supported-file-types — uploadable formats.
 *
 * Proxies `GET {API_URL}/v1/config/supported-file-types`; offline it serves the
 * built-in list.
 */
export async function GET(request: Request) {
  return proxyOr(request, "/v1/config/supported-file-types", () =>
    json<SupportedFileType[]>(SUPPORTED_FILE_TYPES),
  );
}

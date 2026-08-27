import { NextResponse } from "next/server";
import { problem } from "./respond";

/**
 * Proxy an incoming BFF request to the real backend (`apps/api`).
 *
 * Returns `null` when `API_URL` is unset — the caller then serves its offline
 * stub payload so the UI keeps working with no backend. When `API_URL` is set,
 * the upstream response is streamed straight back: JSON bodies (including
 * RFC 9457 problem+json), status code, and content type are preserved, and a
 * `trace-id` / `x-trace-id` response header is surfaced so the client keeps the
 * upstream trace id.
 *
 * The incoming `Authorization: Bearer <jwt>` header is forwarded as-is.
 */

const TRACE_HEADERS = ["trace-id", "x-trace-id", "x-request-id"];

function upstreamBase(): string | null {
  const base = process.env.API_URL;
  return base && base.length > 0 ? base.replace(/\/$/, "") : null;
}

export interface ProxyInit {
  /** Upstream path starting with `/v1/...`. Query string is copied from the incoming URL unless included here. */
  path: string;
  /** Override the forwarded method (defaults to the incoming request's method). */
  method?: string;
  /** Pre-serialised JSON body to send instead of streaming the incoming body. */
  jsonBody?: unknown;
}

export async function proxy(request: Request, init: ProxyInit): Promise<Response | null> {
  const base = upstreamBase();
  if (!base) return null;

  const incoming = new URL(request.url);
  const hasQuery = init.path.includes("?");
  const target = `${base}${init.path}${hasQuery ? "" : incoming.search}`;

  const method = init.method ?? request.method;
  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  for (const h of TRACE_HEADERS) {
    const v = request.headers.get(h);
    if (v) headers.set(h, v);
  }

  const fetchInit: RequestInit & { duplex?: "half" } = { method, headers, cache: "no-store" };
  if (method !== "GET" && method !== "HEAD") {
    if (init.jsonBody !== undefined) {
      headers.set("content-type", "application/json");
      fetchInit.body = JSON.stringify(init.jsonBody);
    } else {
      // Stream the incoming body through untouched (handles multipart uploads).
      const buf = await request.arrayBuffer();
      if (buf.byteLength > 0) {
        fetchInit.body = buf;
        const ct = request.headers.get("content-type");
        if (ct) headers.set("content-type", ct);
      }
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, fetchInit);
  } catch {
    return problem(502, "Upstream unavailable", "Could not reach the API service.");
  }

  const traceId = TRACE_HEADERS.map((h) => upstream.headers.get(h)).find(Boolean) ?? undefined;

  const text = await upstream.text();
  const responseHeaders: Record<string, string> = { "Cache-Control": "no-store" };
  const ct = upstream.headers.get("content-type");
  if (ct) responseHeaders["content-type"] = ct;
  if (traceId) responseHeaders["x-trace-id"] = traceId;

  return new NextResponse(text || null, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

/** Pull an upstream trace id out of a proxied problem+json Response, if any. */
export function traceIdOf(res: Response): string | undefined {
  return res.headers.get("x-trace-id") ?? undefined;
}

/**
 * Proxy the request upstream; when `API_URL` is unset, fall back to the given
 * offline stub. Query string is copied from the incoming URL. Every BFF route
 * handler is one line: `return proxyOr(request, "/v1/…", () => json(stub))`.
 */
export async function proxyOr(
  request: Request,
  path: string,
  stub: () => Response | Promise<Response>,
  init?: Omit<ProxyInit, "path">,
): Promise<Response> {
  const proxied = await proxy(request, { path, ...init });
  return proxied ?? stub();
}

import { NextResponse } from "next/server";

/**
 * Shared helpers for the route handlers under `app/api/*`.
 *
 * These handlers proxy the real backend (`apps/api`, FastAPI) when `API_URL`
 * is set (see `_lib/proxy.ts`). When it is unset they fall back to a
 * correctly-shaped, empty stub payload so the frontend still compiles, renders
 * its loading skeleton, and settles into an empty state instead of crashing.
 */

/** Handlers must never be cached — they read per-request state. */
export const dynamic = "force-dynamic";

export function json<T>(body: T, init?: ResponseInit) {
  return NextResponse.json(body, {
    ...init,
    headers: { "Cache-Control": "no-store", ...init?.headers },
  });
}

function newTraceId(): string {
  return `trace-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * RFC 9457 problem document — matches `ProblemDetail` in lib/schemas.
 *
 * `traceId` prefers an upstream-supplied id (pass the value pulled from the
 * backend's problem body or a trace header) and only synthesises one as a
 * last resort.
 */
export function problem(status: number, title: string, detail?: string, traceId?: string) {
  return NextResponse.json(
    {
      type: "about:blank",
      title,
      status,
      detail,
      traceId: traceId && traceId.length > 0 ? traceId : newTraceId(),
    },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

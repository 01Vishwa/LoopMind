"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRunStore } from "@/lib/stores/runStore";
import {
  RunEventSchema,
  RunStateDTOSchema,
  type RunEvent,
} from "@/lib/schemas/runSchemas";

/**
 * `connecting`   — initial handshake, no data yet.
 * `streaming`    — connection open, events flowing.
 * `reconnecting` — the socket dropped and `EventSource` is retrying with
 *                  `Last-Event-ID`; the last-known state is still valid.
 * `complete`     — a terminal `run.finished` / `run.failed` event arrived; we
 *                  closed the socket deliberately.
 * `error`        — the socket is closed and not retrying; the stream is dead.
 */
export type StreamStatus =
  | "connecting"
  | "streaming"
  | "reconnecting"
  | "complete"
  | "error";

interface UseRunStreamReturn {
  status: StreamStatus;
  events: RunEvent[];
}

/**
 * Subscribe to a run's SSE event stream.
 *
 * Events are applied to the Zustand `runStore` (the primary consumer surface)
 * and also returned here as a reactive array for components that want the raw
 * log. Both `status` and `events` are real React state, so consumers re-render.
 */
export function useRunStream(runId: string): UseRunStreamReturn {
  const applyEvent = useRunStore((s) => s.applyEvent);

  const [status, setStatus] = useState<StreamStatus>("connecting");
  const [events, setEvents] = useState<RunEvent[]>([]);

  // Highest sequence id applied so far. Persists across reconnects so the
  // gap check stays meaningful; `EventSource` resumes from here via
  // `Last-Event-ID`.
  const lastSeqRef = useRef<number>(0);
  // Set after a drop so the first event once we're back is adopted rather
  // than mis-flagged as a gap (the server may resume mid-stream).
  const resumingRef = useRef<boolean>(false);

  const pendingRef = useRef<RunEvent[]>([]);
  const rafRef = useRef<number | null>(null);

  const flush = useCallback(() => {
    rafRef.current = null;
    const pending = pendingRef.current.splice(0);
    if (pending.length === 0) return;
    for (const ev of pending) applyEvent(ev);
    setEvents((prev) => [...prev, ...pending]);
  }, [applyEvent]);

  const scheduleFlush = useCallback(() => {
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(flush);
    }
  }, [flush]);

  const rehydrate = useCallback((id: string) => {
    // Mirrors the old `lib/api/client.ts:getRun` — parse, don't cast.
    void fetch(`/api/v1/runs/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((raw: unknown) => {
        const parsed = RunStateDTOSchema.safeParse(raw);
        if (!parsed.success) return;
        lastSeqRef.current = parsed.data.lastSeq;
        useRunStore.getState().hydrate(parsed.data);
      })
      .catch(() => {
        /* transient — the next event or reconnect will recover */
      });
  }, []);

  useEffect(() => {
    // Reset per-run state.
    lastSeqRef.current = 0;
    resumingRef.current = false;
    pendingRef.current = [];
    setStatus("connecting");
    setEvents([]);

    const es = new EventSource(`/api/v1/runs/${runId}/events`);
    let closedForTerminal = false;

    es.onopen = () => {
      setStatus("streaming");
    };

    es.onmessage = (e: MessageEvent<string>) => {
      const seq = Number(e.lastEventId || 0);

      if (seq > 0) {
        if (resumingRef.current) {
          // First event after a reconnect: adopt wherever the server resumed.
          resumingRef.current = false;
        } else if (lastSeqRef.current > 0 && seq > lastSeqRef.current + 1) {
          // A real gap — we missed events. Re-fetch full state.
          rehydrate(runId);
        }
        lastSeqRef.current = Math.max(lastSeqRef.current, seq);
      }

      let raw: unknown;
      try {
        raw = JSON.parse(e.data);
      } catch {
        return;
      }

      const result = RunEventSchema.safeParse(raw);
      if (!result.success) return;

      const event = result.data;
      pendingRef.current.push(event);
      scheduleFlush();

      if (event.type === "run.finished" || event.type === "run.failed") {
        closedForTerminal = true;
        setStatus("complete");
        es.close();
      }
    };

    es.onerror = () => {
      if (closedForTerminal) return;
      // `EventSource` reconnects on its own unless it has given up.
      if (es.readyState === EventSource.CLOSED) {
        setStatus("error");
      } else {
        resumingRef.current = true;
        setStatus("reconnecting");
      }
    };

    return () => {
      es.close();
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [runId, scheduleFlush, rehydrate]);

  return { status, events };
}

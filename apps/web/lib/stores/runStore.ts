"use client";

import { create } from "zustand";
import type {
  RunPhase,
  PlanStep,
  BacktrackEvent,
  Observation,
  Verdict,
  ArtifactRef,
  RunStateDTO,
  RunEvent,
} from "@/lib/schemas/runSchemas";

export interface RunStore {
  // ── Derived from SSE events ──────────────────────────────────
  phase: RunPhase;
  round: number;
  elapsedMs: number;
  costUsd: number;
  planSteps: PlanStep[];
  backtracks: BacktrackEvent[];
  currentCode: string;
  codeDiffFromPrevious: string | null;
  observations: Map<number, Observation>;
  verdicts: Verdict[];
  answer: string | null;
  artifacts: ArtifactRef[];
  finalStatus: "running" | "succeeded" | "failed" | "cancelled";

  // ── File analysis progress (pre-loop) ────────────────────────
  fileAnalysis: { file: string; done: number; total: number } | null;

  // ── UI state ─────────────────────────────────────────────────
  selectedStepIndex: number | null;
  codeDiffMode: boolean;
  outputAutoScroll: boolean;
  cancelConfirming: boolean;

  // ── Actions ─────────────────────────────────────────────────
  applyEvent: (event: RunEvent) => void;
  selectStep: (index: number | null) => void;
  toggleDiffMode: () => void;
  setOutputAutoScroll: (value: boolean) => void;
  setCancelConfirming: (value: boolean) => void;
  hydrate: (state: RunStateDTO) => void;
  reset: () => void;
}

const initialState = {
  phase: "connecting" as RunPhase,
  round: 0,
  elapsedMs: 0,
  costUsd: 0,
  planSteps: [] as PlanStep[],
  backtracks: [] as BacktrackEvent[],
  currentCode: "",
  codeDiffFromPrevious: null as string | null,
  observations: new Map<number, Observation>(),
  verdicts: [] as Verdict[],
  answer: null as string | null,
  artifacts: [] as ArtifactRef[],
  finalStatus: "running" as const,
  fileAnalysis: null as { file: string; done: number; total: number } | null,
  selectedStepIndex: null as number | null,
  codeDiffMode: false,
  outputAutoScroll: true,
  cancelConfirming: false,
};

export const useRunStore = create<RunStore>()((set, get) => ({
  ...initialState,

  applyEvent: (event: RunEvent) => {
    set((state) => {
      switch (event.type) {
        case "run.started":
          return { phase: "analyzing" };

        case "analyze.progress":
          return {
            phase: "analyzing",
            fileAnalysis: { file: event.file, done: event.done, total: event.total },
          };

        case "plan.step": {
          const steps = [...state.planSteps];
          // Mark all previous active steps as completed
          const updatedSteps = steps.map((s) =>
            s.status === "active" ? { ...s, status: "completed" as const } : s
          );
          updatedSteps.push({ index: event.index, text: event.text, round: event.round, status: "active" });
          return {
            phase: "planning",
            round: event.round,
            planSteps: updatedSteps,
          };
        }

        case "code.generated":
          return {
            phase: "coding",
            currentCode: event.fullSource,
            codeDiffFromPrevious: event.diff || null,
          };

        case "exec.stdout": {
          // Append stdout to the current active step's observation
          const activeStep = state.planSteps.find((s) => s.status === "active");
          if (!activeStep) return { phase: "executing" };
          const obs = state.observations.get(activeStep.index) ?? {
            stepIndex: activeStep.index,
            stdout: "",
            exitCode: -1,
            durationMs: 0,
            artifacts: [],
          };
          const newObs = new Map(state.observations);
          newObs.set(activeStep.index, { ...obs, stdout: obs.stdout + event.chunk });
          return { phase: "executing", observations: newObs };
        }

        case "exec.finished": {
          const activeStep = state.planSteps.find((s) => s.status === "active");
          if (!activeStep) return {};
          const obs = state.observations.get(activeStep.index) ?? {
            stepIndex: activeStep.index,
            stdout: "",
            exitCode: event.exitCode,
            durationMs: event.durationMs,
            artifacts: event.artifacts,
          };
          const newObs = new Map(state.observations);
          newObs.set(activeStep.index, {
            ...obs,
            exitCode: event.exitCode,
            durationMs: event.durationMs,
            artifacts: event.artifacts,
          });
          return { phase: "verifying", observations: newObs, artifacts: event.artifacts };
        }

        case "verify.verdict": {
          const activeStep = state.planSteps.find((s) => s.status === "active");
          const verdict: Verdict = {
            stepIndex: activeStep?.index ?? -1,
            sufficient: event.sufficient,
            reason: event.reason,
            missingAspects: event.missingAspects,
          };
          return {
            phase: "verifying",
            verdicts: [...state.verdicts, verdict],
          };
        }

        case "route.decision": {
          if (event.action === "backtrack" && event.backtrackIndex !== undefined) {
            const backtrack: BacktrackEvent = {
              fromIndex: event.backtrackIndex,
              toIndex: event.backtrackIndex - 1,
              rationale: event.rationale,
            };
            // Mark steps from backtrackIndex onwards as backtracked
            const updatedSteps = state.planSteps.map((s) =>
              s.index >= event.backtrackIndex!
                ? { ...s, status: "backtracked" as const }
                : s
            );
            return {
              phase: "routing",
              backtracks: [...state.backtracks, backtrack],
              planSteps: updatedSteps,
            };
          }
          return { phase: "routing" };
        }

        case "plan.truncated": {
          const updatedSteps = state.planSteps.map((s) =>
            s.index > event.toIndex ? { ...s, status: "backtracked" as const } : s
          );
          return { planSteps: updatedSteps };
        }

        case "debug.attempt":
          return { phase: "debugging" };

        case "budget.warning":
          return { costUsd: event.spentUsd };

        case "run.finished": {
          const completedSteps = state.planSteps.map((s) =>
            s.status === "active" ? { ...s, status: "completed" as const } : s
          );
          return {
            phase: event.status === "succeeded" ? "complete" : event.status === "cancelled" ? "cancelled" : "failed",
            finalStatus: event.status,
            answer: event.answer ?? null,
            planSteps: completedSteps,
          };
        }

        case "run.failed":
          return { phase: "failed", finalStatus: "failed" };

        default:
          return {};
      }
    });
  },

  selectStep: (index) => set({ selectedStepIndex: index }),

  toggleDiffMode: () => set((state) => ({ codeDiffMode: !state.codeDiffMode })),

  setOutputAutoScroll: (value) => set({ outputAutoScroll: value }),

  setCancelConfirming: (value) => set({ cancelConfirming: value }),

  hydrate: (dto: RunStateDTO) => {
    const observations = new Map<number, Observation>();
    Object.entries(dto.observations).forEach(([key, obs]) => {
      observations.set(Number(key), obs);
    });
    set({
      phase: dto.phase as RunPhase,
      round: dto.round,
      elapsedMs: dto.elapsedMs,
      costUsd: dto.costUsd,
      planSteps: dto.planSteps,
      backtracks: dto.backtracks,
      currentCode: dto.currentCode,
      codeDiffFromPrevious: dto.codeDiff,
      observations,
      verdicts: dto.verdicts,
      answer: dto.answer,
      finalStatus: dto.finalStatus ?? "running",
    });
  },

  reset: () => set({ ...initialState, observations: new Map() }),
}));

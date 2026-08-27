"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Info, RotateCcw } from "lucide-react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { SaveButton } from "@/components/settings/SaveButton";
import { SliderField } from "@/components/settings/SliderField";
import { ModelSelector } from "@/components/settings/ModelSelector";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import { getAgentDefaults, saveAgentDefaults, type AgentDefaults } from "@/lib/data/agentDefaults";
import { listProviders, listAvailableModels } from "@/lib/data/providers";

export default function AgentDefaultsPage() {
  const {
    data: settings,
    status: settingsStatus,
    error: settingsError,
    retry: retrySettings,
  } = useResource(getAgentDefaults, []);

  // Whether any provider key is connected gates the model selectors.
  const { data: providers } = useResource(listProviders, []);
  const providerConnected = (providers ?? []).some((p) => p.connected);

  const { data: models } = useResource(
    () => (providers ? listAvailableModels(providers) : Promise.resolve([])),
    [providers],
  );
  const modelOptions = models ?? [];

  const [values, setValues]         = useState<AgentDefaults | null>(null);
  const [savedState, setSavedState] = useState<AgentDefaults | null>(null);
  const [isSaving, setIsSaving]     = useState(false);
  const [resetting, setResetting]   = useState(false);
  const [saveError, setSaveError]   = useState<string | null>(null);

  // Adopt the server's saved values once they resolve.
  useEffect(() => {
    if (settings) {
      setValues(settings.values);
      setSavedState(settings.values);
    }
  }, [settings]);

  const set = <K extends keyof AgentDefaults>(key: K, value: AgentDefaults[K]) =>
    setValues((prev) => (prev ? { ...prev, [key]: value } : prev));

  const isDirty =
    values !== null &&
    savedState !== null &&
    (Object.keys(values) as (keyof AgentDefaults)[]).some((k) => values[k] !== savedState[k]);

  const handleSave = async () => {
    if (!values) return;
    setIsSaving(true);
    try {
      const persisted = await saveAgentDefaults(values);
      setValues(persisted);
      setSavedState(persisted);
      setSaveError(null);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (settings) setValues(settings.recommended);
    setResetting(false);
  };

  const disabledReason = (
    <span>
      No provider connected —{" "}
      <Link href="/settings/api-keys" className="text-vera-accent hover:underline">
        Add an API key first →
      </Link>
    </span>
  );

  if (settingsStatus === "error") {
    return (
      <div className="space-y-6 animate-slide-up">
        <ErrorState error={settingsError} onRetry={retrySettings} />
      </div>
    );
  }

  if (!settings || !values) {
    return (
      <div className="space-y-6 animate-slide-up">
        <SettingsCard
          title="Run Limits"
          description="These defaults apply to all new runs. Individual runs can override them."
        >
          <BlockSkeleton className="max-w-[480px]" lines={4} />
        </SettingsCard>
        <SettingsCard title="Model Configuration" description="Choose which AI models power each agent type.">
          <BlockSkeleton className="max-w-[480px]" lines={3} />
        </SettingsCard>
        <SettingsCard title="File Processing" description="Limits that apply when ingesting files into a workspace.">
          <BlockSkeleton className="max-w-[480px]" lines={3} />
        </SettingsCard>
      </div>
    );
  }

  const { bounds } = settings;

  return (
    <div className="space-y-6 animate-slide-up">
      {saveError && <p className="text-xs text-vera-insufficient">{saveError}</p>}

      {/* ── Run Limits ──────────────────────────────────────── */}
      <SettingsCard
        title="Run Limits"
        description="These defaults apply to all new runs. Individual runs can override them."
      >
        <div className="space-y-8 max-w-[480px]">
          <SliderField
            id="max-rounds"
            label="Max rounds per run"
            min={bounds.maxRounds.min}
            max={bounds.maxRounds.max}
            value={values.maxRounds}
            onChange={(v) => set("maxRounds", v)}
            helpText="How many plan → verify → route cycles the agent runs before stopping. Higher = more thorough but more expensive."
          />

          <div className="space-y-1.5">
            <label htmlFor="max-cost" className="text-sm font-medium text-vera-ink block">
              Max cost per run ($)
            </label>
            <div className="flex items-center gap-2 max-w-[160px]">
              <span className="text-sm text-vera-muted">$</span>
              <input
                id="max-cost"
                type="number"
                min={bounds.maxCostUsd.min}
                max={bounds.maxCostUsd.max}
                step={bounds.maxCostUsd.step}
                value={values.maxCostUsd}
                onChange={(e) => set("maxCostUsd", Number(e.target.value))}
                className="vera-input tabular-nums"
              />
            </div>
            <p className="text-xs text-vera-muted">
              The run stops if this limit is reached. You receive the best answer available so far.
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="max-debug" className="text-sm font-medium text-vera-ink block">
              Max debug attempts
            </label>
            <input
              id="max-debug"
              type="number"
              min={bounds.maxDebugAttempts.min}
              max={bounds.maxDebugAttempts.max}
              value={values.maxDebugAttempts}
              onChange={(e) => set("maxDebugAttempts", Number(e.target.value))}
              className="vera-input tabular-nums max-w-[100px]"
            />
            <p className="text-xs text-vera-muted">
              How many times the agent retries when generated code fails. 0 = no retries.
            </p>
          </div>
        </div>

        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />
      </SettingsCard>

      {/* ── Model Configuration ──────────────────────────────── */}
      <SettingsCard
        title="Model Configuration"
        description="Choose which AI models power each agent type."
      >
        {/* Info callout */}
        <div className="flex gap-2.5 p-3 rounded-md bg-vera-accent-muted border-l-2 border-vera-accent mb-6">
          <Info size={14} strokeWidth={1.75} className="text-vera-accent shrink-0 mt-0.5" />
          <p className="text-xs text-vera-muted leading-relaxed">
            Higher-tier models produce better results but cost more per run. We recommend
            Sonnet-class models for utility agents to balance quality and cost.
            {!providerConnected && (
              <span> Connect a provider key in{" "}
                <Link href="/settings/api-keys" className="text-vera-accent hover:underline">
                  API Keys
                </Link>{" "}
                to enable model selection.
              </span>
            )}
          </p>
        </div>

        <div className="space-y-6 max-w-[480px]">
          <ModelSelector
            id="reasoning-model"
            label="Reasoning agents"
            description="Planner, Coder, Verifier, Router — the core decision-making agents."
            value={values.reasoningModel}
            options={modelOptions}
            onChange={(v) => set("reasoningModel", v)}
            disabled={!providerConnected}
            disabledReason={disabledReason}
          />

          <ModelSelector
            id="utility-model"
            label="Utility agents"
            description="Analyzer, Debugger, Finalizer — lower-cost supporting agents."
            value={values.utilityModel}
            options={modelOptions}
            onChange={(v) => set("utilityModel", v)}
            disabled={!providerConnected}
            disabledReason={disabledReason}
          />
        </div>

        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />
      </SettingsCard>

      {/* ── File Processing ───────────────────────────────────── */}
      <SettingsCard
        title="File Processing"
        description="Limits that apply when ingesting files into a workspace."
      >
        <div className="space-y-6 max-w-[480px]">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label htmlFor="max-files" className="text-sm font-medium text-vera-ink block">
                Max files per workspace
              </label>
              <input
                id="max-files"
                type="number"
                min={bounds.maxFilesPerWorkspace.min}
                max={bounds.maxFilesPerWorkspace.max}
                value={values.maxFilesPerWorkspace}
                onChange={(e) => set("maxFilesPerWorkspace", Number(e.target.value))}
                className="vera-input tabular-nums"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="max-file-mb" className="text-sm font-medium text-vera-ink block">
                Max file size (MB)
              </label>
              <input
                id="max-file-mb"
                type="number"
                min={bounds.maxFileSizeMb.min}
                max={bounds.maxFileSizeMb.max}
                value={values.maxFileSizeMb}
                onChange={(e) => set("maxFileSizeMb", Number(e.target.value))}
                className="vera-input tabular-nums"
              />
            </div>
          </div>

          <SliderField
            id="top-k"
            label="Retriever top-K"
            min={bounds.retrieverTopK.min}
            max={bounds.retrieverTopK.max}
            value={values.retrieverTopK}
            onChange={(v) => set("retrieverTopK", v)}
            helpText="How many file chunks are sent to the Planner per run. Higher = more context but higher cost."
          />
        </div>

        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />

        {/* Reset link */}
        <div className="mt-4">
          {!resetting ? (
            <button
              onClick={() => setResetting(true)}
              className="flex items-center gap-1.5 text-xs text-vera-muted hover:text-vera-ink transition-colors"
            >
              <RotateCcw size={12} strokeWidth={1.75} />
              Reset to recommended defaults
            </button>
          ) : (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-vera-muted">Reset all agent settings to VERA defaults?</span>
              <button onClick={handleReset} className="font-medium text-vera-insufficient hover:underline">
                Reset
              </button>
              <span className="text-vera-border">|</span>
              <button onClick={() => setResetting(false)} className="font-medium text-vera-ink hover:underline">
                Cancel
              </button>
            </div>
          )}
        </div>
      </SettingsCard>
    </div>
  );
}

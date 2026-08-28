"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { Info, RotateCcw } from "lucide-react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { SaveButton } from "@/components/settings/SaveButton";
import { SliderField } from "@/components/settings/SliderField";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { AgentDefaultsResponse, UpdateAgentDefaultsRequest, UpdateAssignment } from "@/lib/data/agentDefaults";
import { modelsCache } from "@/lib/providers/keyStore";

export default function AgentDefaultsPage() {
  const [settings, setSettings] = useState<AgentDefaultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  const [providers, setProviders] = useState<any[]>([]);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  
  const [values, setValues] = useState<UpdateAgentDefaultsRequest | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fetchSettings = async () => {
    try {
      const [defaultsRes, providersRes] = await Promise.all([
        fetch("/api/settings/agent-defaults"),
        fetch("/api/providers")
      ]);
      if (!defaultsRes.ok) throw new Error("Failed to fetch defaults");
      if (!providersRes.ok) throw new Error("Failed to fetch providers");
      
      const defaultsData = await defaultsRes.json();
      const providersData = await providersRes.json();
      
      setSettings(defaultsData);
      setProviders(providersData);
      
      // Transform initial settings to editable values
      setValues({
        max_rounds: defaultsData.max_rounds,
        max_cost_usd: defaultsData.max_cost_usd,
        max_debug_attempts: defaultsData.max_debug_attempts,
        retriever_top_k: defaultsData.retriever_top_k,
        assignments: defaultsData.assignments
          .filter((a: any) => a.provider_connection_id && a.model_id)
          .map((a: any) => ({
            tier: a.tier,
            provider_connection_id: a.provider_connection_id,
            model_id: a.model_id
          }))
      });
      
      // Fetch models from cache for all connected providers
      let models: any[] = [];
      for (const p of providersData) {
        const cachedModels = await modelsCache.get(p.id) || [];
        models = models.concat(cachedModels.map(m => ({ ...m, provider_connection_id: p.id, provider_display_name: p.display_name })));
      }
      setAvailableModels(models);
      
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const set = <K extends keyof UpdateAgentDefaultsRequest>(key: K, value: UpdateAgentDefaultsRequest[K]) =>
    setValues((prev) => (prev ? { ...prev, [key]: value } : prev));
    
  const setAssignment = (tier: "reasoning" | "utility", value: string) => {
    if (!values) return;
    const parts = value.split("::");
    if (parts.length !== 2) return;
    const providerId = parts[0];
    const modelId = parts[1];
    
    const newAssignments = (values.assignments || []).filter(a => a.tier !== tier);
    newAssignments.push({ tier, provider_connection_id: providerId, model_id: modelId });
    set("assignments", newAssignments);
  };

  // Basic diff check for dirtiness
  const isDirty = useMemo(() => {
    if (!settings || !values) return false;
    if (settings.max_rounds !== values.max_rounds) return true;
    if (settings.max_cost_usd !== values.max_cost_usd) return true;
    if (settings.max_debug_attempts !== values.max_debug_attempts) return true;
    if (settings.retriever_top_k !== values.retriever_top_k) return true;
    
    // Assignments check
    const currentMap = Object.fromEntries(
      settings.assignments.map(a => [a.tier, `${a.provider_connection_id}::${a.model_id}`])
    );
    const newMap = Object.fromEntries(
      (values.assignments || []).map(a => [a.tier, `${a.provider_connection_id}::${a.model_id}`])
    );
    
    for (const t of ["reasoning", "utility"]) {
      if (currentMap[t] !== newMap[t] && (currentMap[t] !== "null::null" || newMap[t] !== undefined)) {
        return true;
      }
    }
    return false;
  }, [settings, values]);

  const handleSave = async () => {
    if (!values) return;
    setIsSaving(true);
    try {
      const res = await fetch("/api/settings/agent-defaults", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values)
      });
      if (!res.ok) throw new Error("Save failed");
      const data = await res.json();
      setSettings(data);
      setSaveError(null);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    setIsSaving(true);
    try {
      const res = await fetch("/api/settings/agent-defaults/reset", {
        method: "POST"
      });
      if (!res.ok) throw new Error("Reset failed");
      const data = await res.json();
      setSettings(data);
      setValues({
        max_rounds: data.max_rounds,
        max_cost_usd: data.max_cost_usd,
        max_debug_attempts: data.max_debug_attempts,
        retriever_top_k: data.retriever_top_k,
        assignments: []
      });
      setSaveError(null);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSaving(false);
      setResetting(false);
    }
  };

  if (error) {
    return (
      <div className="space-y-6 animate-slide-up">
        <ErrorState error={error} onRetry={fetchSettings} />
      </div>
    );
  }

  if (loading || !settings || !values) {
    return (
      <div className="space-y-6 animate-slide-up">
        <SettingsCard title="Model Configuration" description="Choose which AI models power each agent type.">
          <BlockSkeleton className="max-w-[480px]" lines={4} />
        </SettingsCard>
      </div>
    );
  }

  const providerConnected = providers.length > 0;
  const missingProviders = (values.assignments || []).some(a => !providers.find(p => p.id === a.provider_connection_id));

  const getTierValue = (tier: string) => {
    const a = (values.assignments || []).find(x => x.tier === tier);
    return a ? `${a.provider_connection_id}::${a.model_id}` : "";
  };

  return (
    <div className="space-y-6 animate-slide-up">
      {saveError && <p className="text-xs text-vera-insufficient">{saveError}</p>}
      {missingProviders && (
        <div className="flex gap-2.5 p-3 rounded-md bg-amber-500/10 border-l-2 border-amber-500">
          <Info size={14} strokeWidth={1.75} className="text-amber-500 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-500 leading-relaxed">
            One or more assigned providers have been removed. Please reconfigure your models.
          </p>
        </div>
      )}

      {/* ── Model Configuration ──────────────────────────────── */}
      <SettingsCard
        title="Model Configuration"
        description="Choose which AI models power each agent type."
      >
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
          {/* Custom Selectors for models */}
          {["reasoning", "utility"].map((tier) => (
            <div key={tier} className="space-y-1.5">
              <label className="text-sm font-medium text-vera-ink block capitalize">
                {tier} agents
              </label>
              {!providerConnected ? (
                <div className="px-3 py-2 bg-vera-surface border border-vera-border rounded-md text-sm text-vera-muted">
                  No provider connected — Add an API key first →
                </div>
              ) : (
                <select 
                  className="w-full vera-input text-sm"
                  value={getTierValue(tier)}
                  onChange={(e) => setAssignment(tier as any, e.target.value)}
                >
                  <option value="" disabled>Select a model...</option>
                  {availableModels.map(m => (
                    <option key={`${m.provider_connection_id}::${m.model_id}`} value={`${m.provider_connection_id}::${m.model_id}`}>
                      {m.provider_display_name} - {m.display_name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>

        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />
      </SettingsCard>

      {/* ── Run Limits ──────────────────────────────────────── */}
      <SettingsCard
        title="Run Limits"
        description="These defaults apply to all new runs. Individual runs can override them."
      >
        <div className="space-y-8 max-w-[480px]">
          <SliderField
            id="max-rounds"
            label="Max rounds per run"
            min={1} max={20}
            value={values.max_rounds || 7}
            onChange={(v) => set("max_rounds", v)}
            helpText="How many plan → verify → route cycles the agent runs before stopping."
          />
          <div className="space-y-1.5">
            <label htmlFor="max-cost" className="text-sm font-medium text-vera-ink block">Max cost per run ($)</label>
            <input
              id="max-cost" type="number" step="0.10"
              min={0.10} max={50.0}
              value={values.max_cost_usd}
              onChange={(e) => set("max_cost_usd", Number(e.target.value))}
              className="vera-input tabular-nums max-w-[160px]"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="max-debug" className="text-sm font-medium text-vera-ink block">Max debug attempts</label>
            <input
              id="max-debug" type="number"
              min={1} max={10}
              value={values.max_debug_attempts}
              onChange={(e) => set("max_debug_attempts", Number(e.target.value))}
              className="vera-input tabular-nums max-w-[100px]"
            />
          </div>
        </div>
        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />
      </SettingsCard>

      {/* ── File Processing ───────────────────────────────────── */}
      <SettingsCard title="File Processing" description="Limits that apply when ingesting files into a workspace.">
        <div className="space-y-6 max-w-[480px]">
          <SliderField
            id="top-k" label="Retriever top-K"
            min={1} max={50}
            value={values.retriever_top_k || 12}
            onChange={(v) => set("retriever_top_k", v)}
            helpText="How many file chunks are sent to the Planner per run."
          />
        </div>
        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />
        
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
              <button onClick={handleReset} className="font-medium text-vera-insufficient hover:underline">Reset</button>
              <span className="text-vera-border">|</span>
              <button onClick={() => setResetting(false)} className="font-medium text-vera-ink hover:underline">Cancel</button>
            </div>
          )}
        </div>
      </SettingsCard>
    </div>
  );
}

"use client";

import { SettingsCard } from "@/components/settings/SettingsCard";
import { ProviderKeyCard } from "@/components/settings/ProviderKeyCard";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import { listProviders } from "@/lib/data/providers";
import { Info } from "lucide-react";

export default function ApiKeysPage() {
  const { data: providers, status, error, retry } = useResource(listProviders, []);

  return (
    <div className="space-y-6 animate-slide-up">
      <SettingsCard
        title="API Keys & Model Providers"
        description="Connect your own provider keys. VERA uses them to call AI models on your behalf — you pay the provider directly and keep full control over model access."
      >
        {/* Info callout */}
        <div className="flex gap-2.5 p-3 rounded-md bg-vera-accent-muted border-l-2 border-vera-accent mb-6">
          <Info size={14} strokeWidth={1.75} className="text-vera-accent shrink-0 mt-0.5" />
          <p className="text-xs text-vera-muted leading-relaxed">
            Your keys are stored locally and never sent to VERA servers. VERA calls model
            provider APIs directly from your browser session using the keys you provide.
            Keys are masked after saving and only decrypted in memory when a run is
            triggered.
          </p>
        </div>

        <div className="space-y-4">
          {status === "loading" && <BlockSkeleton lines={3} />}
          {status === "error" && <ErrorState error={error} onRetry={retry} />}
          {status === "success" && providers?.length === 0 && (
            <p className="text-xs text-vera-muted">
              No model providers are enabled for this workspace yet.
            </p>
          )}
          {status === "success" &&
            providers?.map((p) => (
              <ProviderKeyCard
                key={p.id}
                name={p.name}
                description={p.description}
                keyPrefix={p.keyPrefix}
                docsUrl={p.docsUrl}
                icon={p.icon}
                accentColor={p.accentColor}
              />
            ))}
        </div>

        <p className="text-xs text-vera-muted mt-4">
          Need a different provider?{" "}
          <a
            href="mailto:support@vera.ai"
            className="text-vera-accent hover:underline"
          >
            Request an integration →
          </a>
        </p>
      </SettingsCard>

      {/* How keys are used */}
      <SettingsCard title="How your keys are used">
        <div className="space-y-4">
          {[
            {
              step: "1",
              title: "Save your provider key above",
              body: "VERA masks the key immediately. Only the last 4 characters are shown.",
            },
            {
              step: "2",
              title: "Configure model tiers in Agent Defaults",
              body: "Choose which models power each agent type. Defaults work without any configuration.",
            },
            {
              step: "3",
              title: "VERA routes requests via your key",
              body: "When a run starts, VERA calls the provider API with your key. Billing goes directly to your provider account.",
            },
          ].map(({ step, title, body }) => (
            <div key={step} className="flex gap-3">
              <div className="w-6 h-6 rounded-full bg-vera-accent-muted text-vera-accent text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                {step}
              </div>
              <div>
                <p className="text-sm font-medium text-vera-ink">{title}</p>
                <p className="text-xs text-vera-muted mt-0.5">{body}</p>
              </div>
            </div>
          ))}
        </div>
      </SettingsCard>
    </div>
  );
}

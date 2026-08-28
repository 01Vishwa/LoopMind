"use client";

import { useEffect, useState } from "react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { ProviderKeyCard } from "@/components/settings/ProviderKeyCard";
import { BlockSkeleton, ErrorState } from "@/components/shared/DataStates";
import { Info } from "lucide-react";

export default function ApiKeysPage() {
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchConnections = async () => {
    try {
      const res = await fetch("/api/providers");
      if (!res.ok) throw new Error("Failed to fetch providers");
      const data = await res.json();
      setConnections(data);
    } catch (e: any) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnections();
  }, []);

  const openRouterConn = connections.find(c => c.kind === "openrouter");
  const nvidiaConn = connections.find(c => c.kind === "nvidia_nim");

  return (
    <div className="space-y-6 animate-slide-up">
      <SettingsCard
        title="API Keys & Model Providers"
        description="Connect your own provider keys."
      >
        <div className="flex gap-2.5 p-3 rounded-md bg-vera-accent-muted border-l-2 border-vera-accent mb-6">
          <Info size={14} strokeWidth={1.75} className="text-vera-accent shrink-0 mt-0.5" />
          <p className="text-xs text-vera-muted leading-relaxed">
            Your keys are stored locally and never sent to VERA servers. VERA calls model
            provider APIs directly from your browser session using the keys you provide.
            Stored in your browser only — clearing site data or switching browsers/devices means reconnecting.
          </p>
        </div>

        <div className="space-y-4">
          {loading && <BlockSkeleton lines={3} />}
          {error && <ErrorState error={error} onRetry={fetchConnections} />}
          {!loading && !error && (
            <>
              <ProviderKeyCard
                id="openrouter"
                connectionId={openRouterConn?.id}
                name="OpenRouter"
                description="Access 200+ models through a single unified API key."
                keyPrefix="sk-or-v1-"
                docsUrl="https://openrouter.ai/keys"
                icon="🔀"
                onConnected={fetchConnections}
                onRemoved={fetchConnections}
              />
              <ProviderKeyCard
                id="nvidia_nim"
                connectionId={nvidiaConn?.id}
                name="NVIDIA NIM"
                description="Run optimised NVIDIA models — Llama 3.1, Mistral, and more."
                keyPrefix="nvapi-"
                docsUrl="https://build.nvidia.com/nim"
                icon="⚡"
                onConnected={fetchConnections}
                onRemoved={fetchConnections}
              />
            </>
          )}
        </div>
      </SettingsCard>
    </div>
  );
}

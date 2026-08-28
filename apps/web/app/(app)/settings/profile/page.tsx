"use client";

import { useState, useEffect } from "react";
import { Lock } from "lucide-react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { SaveButton } from "@/components/settings/SaveButton";
import { cn } from "@/lib/utils/cn";

import { useAuth } from "@/lib/auth/AuthProvider";
import { updateProfile } from "@/lib/data/session";
import type { RunMode } from "@/lib/config/modes";
import { STRINGS } from "@/lib/config/strings";

export default function ProfilePage() {
  const { user, refresh } = useAuth();
  const [name, setName]           = useState("");
  const [savedName, setSavedName] = useState("");

  // Hydrate the editable fields once the session resolves.
  useEffect(() => {
    if (user) {
      setName(user.name);
      setSavedName(user.name);
    }
  }, [user]);
  const [runMode, setRunMode]       = useState<RunMode>("research");
  const [savedRm, setSavedRm]       = useState<RunMode>("research");
  const [isSaving, setIsSaving]     = useState(false);
  const isDirty =
    name !== savedName ||
    runMode !== savedRm;

  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateProfile({
        name,
        timezone: "America/New_York",
        dateFormat: "mdy",
        defaultRunMode: runMode,
      });
      setSavedName(name);
      setSavedRm(runMode);
      setSaveError(null);
      // Keep the sidebar and every other consumer in step with the new name.
      refresh();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      {saveError && <p className="text-xs text-vera-insufficient">{saveError}</p>}

      {/* ── Avatar & Identity ─────────────────────────────── */}
      <SettingsCard title="Profile" description="Your identity across VERA.">
        {/* Name field */}
        <div className="space-y-5 max-w-[480px]">
          <div className="space-y-1.5">
            <label htmlFor="profile-name" className="text-sm font-medium text-vera-ink block">
              Full name
            </label>
            <input
              id="profile-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="vera-input"
            />
          </div>

          {/* Email — read-only (SSO managed) */}
          <div className="space-y-1.5">
            <label htmlFor="profile-email" className="text-sm font-medium text-vera-ink flex items-center gap-1.5">
              Email
              {user?.emailManaged && (
                <span
                  className="flex items-center gap-1 text-xs text-vera-muted font-normal bg-vera-border-subtle px-1.5 py-0.5 rounded"
                  title={STRINGS.settings.emailManagedHelp}
                >
                  <Lock size={10} strokeWidth={1.75} />
                  {STRINGS.settings.emailReadOnlyBadge}
                </span>
              )}
            </label>
            <input
              id="profile-email"
              type="email"
              value={user?.email ?? ""}
              readOnly
              className={cn(
                "vera-input",
                user?.emailManaged && "opacity-60 cursor-not-allowed select-none"
              )}
            />
            {user && user.authProvider !== "local" && (
              <p className="text-xs text-vera-muted">{STRINGS.settings.emailManagedHelp}</p>
            )}
          </div>
        </div>

        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} />
      </SettingsCard>

      {/* ── Preferences ───────────────────────────────────── */}
      <SettingsCard>
        <div className="space-y-6 max-w-[480px]">
          {/* Default run mode */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-vera-ink">Default run mode</p>
            <div className="flex gap-6">
              {(["precise", "research"] as const).map((mode) => (
                <label key={mode} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="runMode"
                    value={mode}
                    checked={runMode === mode}
                    onChange={() => setRunMode(mode)}
                    className="accent-vera-accent"
                  />
                  <span className="text-sm text-vera-ink capitalize">
                    {mode === "precise" ? "Precise" : "Deep research"}
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-vera-muted">
              Deep research uses more rounds and costs more per run but produces better results.
            </p>
          </div>
        </div>

        <SaveButton isDirty={isDirty} isSaving={isSaving} onSave={handleSave} label="Save preferences" />
      </SettingsCard>
    </div>
  );
}

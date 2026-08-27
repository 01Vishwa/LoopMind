"use client";

import { useState, useRef, useEffect } from "react";
import { Lock } from "lucide-react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { SaveButton } from "@/components/settings/SaveButton";
import { DangerZone } from "@/components/settings/DangerZone";
import { cn } from "@/lib/utils/cn";

import { useAuth } from "@/lib/auth/AuthProvider";
import { initialsOf, updateProfile } from "@/lib/data/session";
import type { RunMode } from "@/lib/config/modes";
import { STRINGS } from "@/lib/config/strings";

// Canonical IANA timezone list (abbreviated for demo)
const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "America/Vancouver",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/Moscow",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
  "Pacific/Auckland",
];

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
  const [timezone, setTimezone]   = useState(() => {
    try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { return "America/New_York"; }
  });
  const [savedTz, setSavedTz]       = useState(timezone);
  const [dateFormat, setDateFormat] = useState<"mdy" | "dmy">("mdy");
  const [savedDf, setSavedDf]       = useState<"mdy" | "dmy">("mdy");
  const [runMode, setRunMode]       = useState<RunMode>("research");
  const [savedRm, setSavedRm]       = useState<RunMode>("research");
  const [isSaving, setIsSaving]     = useState(false);

  const avatarInputRef = useRef<HTMLInputElement>(null);

  const isDirty =
    name !== savedName ||
    timezone !== savedTz ||
    dateFormat !== savedDf ||
    runMode !== savedRm;

  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateProfile({
        name,
        timezone,
        dateFormat,
        defaultRunMode: runMode,
      });
      setSavedName(name);
      setSavedTz(timezone);
      setSavedDf(dateFormat);
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
        {/* Avatar row */}
        <div className="flex items-center gap-5 mb-6 pb-6 border-b border-vera-border">
          <div
            className="w-16 h-16 rounded-full bg-vera-accent-muted border-2 border-vera-accent/20
                       flex items-center justify-center shrink-0 cursor-pointer
                       hover:border-vera-accent/50 transition-colors"
            onClick={() => avatarInputRef.current?.click()}
            title="Change avatar"
          >
            <span className="text-xl font-bold text-vera-accent">{name ? initialsOf(name) : ""}</span>
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-vera-ink">{savedName}</span>
            <span className="text-xs text-vera-muted">{user?.email ?? ""}</span>
            <button
              onClick={() => avatarInputRef.current?.click()}
              className="mt-2 text-xs text-vera-accent hover:underline text-left w-fit"
            >
              Change avatar
            </button>
          </div>
          <input
            ref={avatarInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp"
            className="hidden"
            onChange={() => {/* avatar upload handler */}}
          />
        </div>

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
              readOnly={user?.emailManaged ?? true}
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

        <DangerZone
          description="Permanently delete your account and all associated data. This action cannot be undone."
          buttonLabel="Delete account"
          confirmLabel="Yes, delete my account"
          onConfirm={() => alert("Account deletion requested")}
        />
      </SettingsCard>

      {/* ── Preferences ───────────────────────────────────── */}
      <SettingsCard title="Preferences" description="Display and workflow preferences.">
        <div className="space-y-6 max-w-[480px]">
          {/* Timezone */}
          <div className="space-y-1.5">
            <label htmlFor="timezone" className="text-sm font-medium text-vera-ink block">
              Timezone
            </label>
            <select
              id="timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="vera-input appearance-none bg-no-repeat"
              style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238B8B9E' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\")", backgroundRepeat: "no-repeat", backgroundPosition: "right 12px center", paddingRight: "2rem" }}
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>{tz.replace("_", " ")}</option>
              ))}
            </select>
          </div>

          {/* Date format */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-vera-ink">Date format</p>
            <div className="flex gap-6">
              {(["mdy", "dmy"] as const).map((fmt) => (
                <label key={fmt} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="dateFormat"
                    value={fmt}
                    checked={dateFormat === fmt}
                    onChange={() => setDateFormat(fmt)}
                    className="accent-vera-accent"
                  />
                  <span className="text-sm text-vera-ink">
                    {fmt === "mdy" ? "MM/DD/YYYY" : "DD/MM/YYYY"}
                  </span>
                </label>
              ))}
            </div>
          </div>

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

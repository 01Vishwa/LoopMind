"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Zap, Eye, EyeOff } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const router = useRouter();
  
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"checking" | "invalid" | "ready" | "success">("checking");
  const [sessionToken, setSessionToken] = useState<string | null>(null);

  const hasLength = password.length >= 8;
  const hasNumber = /\d/.test(password);

  useEffect(() => {
    // Check for recovery session on mount
    const checkSession = async () => {
      const supabase = createClient();
      const { data: { session }, error } = await supabase.auth.getSession();
      
      if (error || !session) {
        setStatus("invalid");
      } else {
        setSessionToken(session.access_token);
        setStatus("ready");
      }
    };
    
    checkSession();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!hasLength || !hasNumber) return;

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/v1/auth/reset-password", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ password, password_confirm: passwordConfirm }),
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 429) {
          setError("Too many attempts. Try again in a few minutes.");
        } else {
          const data = await res.json().catch(() => null);
          setError(data?.detail && typeof data.detail === "string" ? data.detail : "Could not reset password. Please try again.");
          if (Array.isArray(data?.detail)) {
             setError(data.detail[0].msg);
          }
        }
        return;
      }

      setStatus("success");
    } catch {
      setError("Could not reach the server. Check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  if (status === "checking") {
    return (
      <div className="w-full max-w-[400px] px-4 flex justify-center py-12">
        <span className="w-6 h-6 border-2 border-vera-accent/40 border-t-vera-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (status === "invalid") {
    return (
      <div className="w-full max-w-[400px] px-4">
        <div className="rounded-2xl border border-vera-border p-8 shadow-xl shadow-black/10 text-center" style={{ background: "var(--vera-surface)" }}>
          <h1 className="text-xl font-semibold text-vera-ink mb-4">Link expired</h1>
          <p className="text-sm text-vera-muted mb-8">
            This link has expired or was already used.
          </p>
          <Link href="/auth/forgot-password" className="text-sm text-vera-accent hover:underline">
            Request a new link
          </Link>
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="w-full max-w-[400px] px-4">
        <div className="rounded-2xl border border-vera-border p-8 shadow-xl shadow-black/10 text-center" style={{ background: "var(--vera-surface)" }}>
          <div className="flex flex-col items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-vera-accent flex items-center justify-center shadow-lg shadow-vera-accent/30">
              <Zap size={18} strokeWidth={2} className="text-white" />
            </div>
            <div className="text-center">
              <p className="text-lg font-bold tracking-tight text-vera-ink" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.03em" }}>VERA</p>
            </div>
          </div>
          
          <h1 className="text-xl font-semibold text-vera-ink mb-4">Password updated</h1>
          <p className="text-sm text-vera-muted mb-8">
            Your password has been successfully updated.
          </p>

          <button
            onClick={() => {
              // Sign out locally to clear the recovery session
              const supabase = createClient();
              supabase.auth.signOut().then(() => {
                router.push("/login");
              });
            }}
            className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white transition-all duration-150"
            style={{ background: "var(--vera-accent)", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}
          >
            Please log in
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[400px] px-4">
      <div className="rounded-2xl border border-vera-border p-8 shadow-xl shadow-black/10" style={{ background: "var(--vera-surface)" }}>
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-vera-accent flex items-center justify-center shadow-lg shadow-vera-accent/30">
            <Zap size={18} strokeWidth={2} className="text-white" />
          </div>
          <div className="text-center">
            <p className="text-lg font-bold tracking-tight text-vera-ink" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.03em" }}>VERA</p>
          </div>
        </div>

        <h1 className="text-xl font-semibold text-vera-ink text-center mb-6">
          Set new password
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* Password */}
          <div className="space-y-1.5">
            <label htmlFor="reset-password" className="text-sm font-medium text-vera-ink block">
              New Password
            </label>
            <div className="relative">
              <input
                id="reset-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="vera-input w-full pr-10"
                disabled={isLoading}
              />
              <button
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-vera-muted hover:text-vera-ink transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            
            <div className="text-[11px] space-y-1 mt-1">
              <p className={hasLength ? "text-green-500" : "text-vera-muted"}>
                ✓ Minimum 8 characters
              </p>
              <p className={hasNumber ? "text-green-500" : "text-vera-muted"}>
                ✓ Contains a number
              </p>
            </div>
          </div>

          {/* Confirm Password */}
          <div className="space-y-1.5">
            <label htmlFor="reset-password-confirm" className="text-sm font-medium text-vera-ink block">
              Confirm New Password
            </label>
            <div className="relative">
              <input
                id="reset-password-confirm"
                type={showPasswordConfirm ? "text" : "password"}
                autoComplete="new-password"
                required
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="••••••••"
                className="vera-input w-full pr-10"
                disabled={isLoading}
              />
              <button
                type="button"
                aria-label={showPasswordConfirm ? "Hide password" : "Show password"}
                onClick={() => setShowPasswordConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-vera-muted hover:text-vera-ink transition-colors"
                tabIndex={-1}
              >
                {showPasswordConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {error && (
            <p className="text-xs font-medium px-3 py-2 rounded-md" style={{ color: "var(--vera-insufficient)", background: "color-mix(in srgb, var(--vera-insufficient) 10%, transparent)" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading || !password || !passwordConfirm || !hasLength || !hasNumber}
            className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "var(--vera-accent)", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}
          >
            {isLoading ? "Updating..." : "Update password"}
          </button>
        </form>
      </div>
    </div>
  );
}

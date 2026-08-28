"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Zap, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/workspaces";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setErrorType(null);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 429) {
          setError("Too many attempts. Try again in a few minutes.");
          setErrorType("rate_limit");
          return;
        }

        const data = await res.json().catch(() => null);
        if (data?.detail === "email_not_confirmed") {
          setError("Check your email to confirm your account first.");
          setErrorType("email_not_confirmed");
        } else {
          setError("Invalid email or password.");
          setErrorType("invalid_credentials");
        }
        return;
      }

      // We rely on middleware and cookie being set implicitly by FastAPI? 
      // Wait, FastAPI returns access_token/refresh_token in the body.
      // Next.js middleware using `@supabase/ssr` relies on cookies.
      // Supabase's `supabase.auth.signInWithPassword` in the client SDK sets the cookies/local storage.
      // But we are calling FastAPI directly! 
      // If we call FastAPI directly, we need to pass tokens back to the client or use `supabase.auth.setSession()`.
      // Let's use the Supabase client directly for login, or set the session if we call FastAPI.
      // Since FastAPI `login` endpoint just delegates to `supabase.auth.sign_in_with_password` and we want Next.js to know about it,
      // the easiest way is to just use `@supabase/ssr` client here, OR take the tokens from FastAPI and set them.
      // Since the prompt explicitly specifies calling `/auth/login` (FastAPI), we should take tokens and call `supabase.auth.setSession()`.

      const data = await res.json();
      const { createClient } = await import("@/lib/supabase/client");
      const supabase = createClient();
      await supabase.auth.setSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });

      // Set the session hint cookie for middleware
      document.cookie = "vera-session=1; path=/;";

      router.push(next);
    } catch {
      setError("Could not reach the server. Check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[400px] px-4">
      {/* Card */}
      <div
        className="rounded-2xl border border-vera-border p-8 shadow-xl shadow-black/10"
        style={{ background: "var(--vera-surface)" }}
      >
        {/* Logo */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-vera-accent flex items-center justify-center shadow-lg shadow-vera-accent/30">
            <Zap size={18} strokeWidth={2} className="text-white" />
          </div>
          <div className="text-center">
            <p
              className="text-lg font-bold tracking-tight text-vera-ink"
              style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.03em" }}
            >
              VERA
            </p>
            <p className="text-[11px] text-vera-muted tracking-widest uppercase mt-0.5">
              Analytics
            </p>
          </div>
        </div>

        <h1 className="text-xl font-semibold text-vera-ink text-center mb-6">
          Welcome back
        </h1>

        {searchParams.get("error") === "link_expired" && (
          <div className="mb-4 text-xs font-medium px-3 py-2 rounded-md"
            style={{
              color: "var(--vera-insufficient)",
              background: "color-mix(in srgb, var(--vera-insufficient) 10%, transparent)",
            }}>
            This link has expired. Please log in or request a new one.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* Email */}
          <div className="space-y-1.5">
            <label htmlFor="login-email" className="text-sm font-medium text-vera-ink block">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="vera-input w-full"
              disabled={isLoading}
            />
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label htmlFor="login-password" className="text-sm font-medium text-vera-ink block">
                Password
              </label>
              <Link
                href="/auth/forgot-password"
                className="text-xs text-vera-accent hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
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
          </div>

          {/* Inline error */}
          {error && (
            <div
              id="login-error"
              role="alert"
              className="text-xs font-medium px-3 py-2 rounded-md space-y-1"
              style={{
                color: "var(--vera-insufficient)",
                background: "color-mix(in srgb, var(--vera-insufficient) 10%, transparent)",
              }}
            >
              <p>{error}</p>
              {errorType === "email_not_confirmed" && (
                <button
                  type="button"
                  className="underline opacity-80 hover:opacity-100"
                  onClick={async () => {
                     // In a real app we'd call a resend endpoint. For now just show message.
                     alert("In a real app, this would resend the confirmation email.");
                  }}
                >
                  Resend confirmation
                </button>
              )}
            </div>
          )}

          {/* Submit */}
          <button
            id="login-submit"
            type="submit"
            disabled={isLoading || !email || !password}
            className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: isLoading
                ? "var(--vera-accent)"
                : "var(--vera-accent)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
            }}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Logging in…
              </span>
            ) : (
              "Log in"
            )}
          </button>
        </form>

        {/* Sign up link */}
        <p className="text-center text-sm text-vera-muted mt-6">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="text-vera-accent font-medium hover:underline"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

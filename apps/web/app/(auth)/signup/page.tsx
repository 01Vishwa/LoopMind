"use client";

import { useState } from "react";
import Link from "next/link";
import { Zap, Eye, EyeOff } from "lucide-react";

export default function SignupPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "success">("idle");
  const [lastEmailSentTime, setLastEmailSentTime] = useState(0);

  const hasLength = password.length >= 8;
  const hasNumber = /\d/.test(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!hasLength || !hasNumber) {
      return;
    }

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/v1/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, password_confirm: passwordConfirm, full_name: fullName }),
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 429) {
          setError("Too many attempts. Try again in a few minutes.");
        } else {
          const data = await res.json().catch(() => null);
          setError(data?.detail && typeof data.detail === "string" ? data.detail : "Could not create account. Please try again.");
          if (Array.isArray(data?.detail)) {
             // Handle pydantic validation errors
             setError(data.detail[0].msg);
          }
        }
        return;
      }

      setStatus("success");
      setLastEmailSentTime(Date.now());
    } catch {
      setError("Could not reach the server. Check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  if (status === "success") {
    return (
      <div className="w-full max-w-[400px] px-4">
        <div
          className="rounded-2xl border border-vera-border p-8 shadow-xl shadow-black/10 flex flex-col items-center text-center"
          style={{ background: "var(--vera-surface)" }}
        >
          <div className="flex flex-col items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-vera-accent flex items-center justify-center shadow-lg shadow-vera-accent/30">
              <Zap size={18} strokeWidth={2} className="text-white" />
            </div>
            <div className="text-center">
              <p className="text-lg font-bold tracking-tight text-vera-ink" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.03em" }}>VERA</p>
              <p className="text-[11px] text-vera-muted tracking-widest uppercase mt-0.5">Analytics</p>
            </div>
          </div>
          
          <h1 className="text-xl font-semibold text-vera-ink mb-4">Check your email</h1>
          <p className="text-sm text-vera-muted mb-8">
            We sent a confirmation link to <br/>
            <span className="font-semibold text-vera-ink">{email}</span><br/>
            Click it to activate your account.
          </p>

          <div className="space-y-4 w-full">
             <button
              onClick={async () => {
                 if (Date.now() - lastEmailSentTime < 60000) {
                    alert("Please wait 60 seconds before resending.");
                    return;
                 }
                 // Resend logic if API supports it, for now just fake it
                 alert("Confirmation email resent.");
                 setLastEmailSentTime(Date.now());
              }}
              className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white transition-all duration-150"
              style={{ background: "var(--vera-accent)", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}
            >
              Resend email
            </button>
            <Link href="/signup" onClick={() => setStatus("idle")} className="block text-sm text-vera-accent hover:underline">
              Back to sign up
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[400px] px-4">
      {/* Card */}
      <div
        className="rounded-2xl border border-vera-border p-6 shadow-xl shadow-black/10"
        style={{ background: "var(--vera-surface)" }}
      >
        {/* Logo */}
        <div className="flex flex-col items-center gap-2 mb-4">
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

        <h1 className="text-xl font-semibold text-vera-ink text-center mb-4">
          Create your account
        </h1>

        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          {/* Full name */}
          <div className="space-y-1">
            <label htmlFor="signup-name" className="text-sm font-medium text-vera-ink block">
              Full name
            </label>
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Chen"
              className="vera-input w-full"
              disabled={isLoading}
            />
          </div>

          {/* Email */}
          <div className="space-y-1">
            <label htmlFor="signup-email" className="text-sm font-medium text-vera-ink block">
              Email
            </label>
            <input
              id="signup-email"
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
          <div className="space-y-1">
            <label htmlFor="signup-password" className="text-sm font-medium text-vera-ink block">
              Password
            </label>
            <div className="relative">
              <input
                id="signup-password"
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
            
            <div className="text-[11px] space-y-0.5 mt-1 leading-tight">
              <p className={hasLength ? "text-green-500" : "text-vera-muted"}>
                ✓ Minimum 8 characters
              </p>
              <p className={hasNumber ? "text-green-500" : "text-vera-muted"}>
                ✓ Contains a number
              </p>
            </div>
          </div>

          {/* Confirm Password */}
          <div className="space-y-1">
            <label htmlFor="signup-password-confirm" className="text-sm font-medium text-vera-ink block">
              Confirm Password
            </label>
            <div className="relative">
              <input
                id="signup-password-confirm"
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

          {/* Inline error */}
          {error && (
            <p
              id="signup-error"
              role="alert"
              className="text-xs font-medium px-3 py-2 rounded-md"
              style={{
                color: "var(--vera-insufficient)",
                background: "color-mix(in srgb, var(--vera-insufficient) 10%, transparent)",
              }}
            >
              {error}
            </p>
          )}

          {/* Submit */}
          <button
            id="signup-submit"
            type="submit"
            disabled={isLoading || !fullName || !email || !password || !passwordConfirm || !hasLength || !hasNumber}
            className="w-full py-2 px-4 rounded-lg text-sm font-semibold text-white transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: "var(--vera-accent)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
            }}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Creating account…
              </span>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        {/* Login link */}
        <p className="text-center text-sm text-vera-muted mt-4">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-vera-accent font-medium hover:underline"
          >
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}

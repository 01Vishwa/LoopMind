"use client";

import { useState } from "react";
import Link from "next/link";
import { Zap } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success">("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
        cache: "no-store",
      });

      if (!res.ok) {
        if (res.status === 429) {
          setError("Too many attempts. Try again in a few minutes.");
        } else {
          setError("Something went wrong. Please try again.");
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
            </div>
          </div>
          
          <h1 className="text-xl font-semibold text-vera-ink mb-4">Check your email</h1>
          <p className="text-sm text-vera-muted mb-8">
            If an account exists for <span className="font-semibold text-vera-ink">{email}</span>, we&apos;ve sent a reset link.
          </p>

          <Link href="/login" className="block text-sm text-vera-accent hover:underline">
            Back to log in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[400px] px-4">
      <div
        className="rounded-2xl border border-vera-border p-8 shadow-xl shadow-black/10"
        style={{ background: "var(--vera-surface)" }}
      >
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-vera-accent flex items-center justify-center shadow-lg shadow-vera-accent/30">
            <Zap size={18} strokeWidth={2} className="text-white" />
          </div>
          <div className="text-center">
            <p className="text-lg font-bold tracking-tight text-vera-ink" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.03em" }}>VERA</p>
          </div>
        </div>

        <h1 className="text-xl font-semibold text-vera-ink text-center mb-6">
          Reset your password
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-1.5">
            <label htmlFor="forgot-email" className="text-sm font-medium text-vera-ink block">
              Email
            </label>
            <input
              id="forgot-email"
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

          {error && (
            <p className="text-xs font-medium px-3 py-2 rounded-md" style={{ color: "var(--vera-insufficient)", background: "color-mix(in srgb, var(--vera-insufficient) 10%, transparent)" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading || !email}
            className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "var(--vera-accent)", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" }}
          >
            {isLoading ? "Sending..." : "Send reset link"}
          </button>
        </form>

        <p className="text-center text-sm text-vera-muted mt-6">
          <Link href="/login" className="text-vera-accent font-medium hover:underline">
            Back to log in
          </Link>
        </p>
      </div>
    </div>
  );
}

/**
 * Unauthenticated shell layout — no sidebar, just centered content.
 * Used by /login and /signup.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "var(--vera-paper)" }}
    >
      {children}
    </div>
  );
}

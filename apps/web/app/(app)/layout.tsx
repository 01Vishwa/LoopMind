import { Sidebar } from "@/components/shared/Sidebar";
import { AuthProvider } from "@/lib/auth/AuthProvider";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--vera-paper)" }}>
      {/* Skip link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-vera-accent focus:text-white focus:rounded text-label"
      >
        Skip to main content
      </a>

      {/* Sidebar */}
      <Sidebar />

      {/* Main area */}
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        {/* Scrollable content */}
        <main
          id="main-content"
          className="flex-1 overflow-auto"
          style={{ background: "var(--vera-paper)" }}
        >
          {children}
        </main>
      </div>
    </div>
    </AuthProvider>
  );
}

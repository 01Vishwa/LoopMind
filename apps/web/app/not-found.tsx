import Link from "next/link";

/** Shown for unmatched routes and explicit `notFound()` calls. */
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <p
        className="text-mono-ui text-vera-muted mb-2"
        style={{ fontSize: "11px", letterSpacing: "0.1em" }}
      >
        404
      </p>
      <p
        className="text-heading text-vera-ink font-medium mb-1"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        Page not found
      </p>
      <p className="text-label text-vera-muted mb-6 max-w-md">
        The page you are looking for does not exist or has moved.
      </p>
      <Link
        href="/workspaces"
        className="inline-flex items-center gap-1.5 px-4 py-2 text-label font-medium text-white bg-vera-accent rounded hover:bg-vera-accent-hover transition-colors no-underline"
        style={{ borderRadius: "6px" }}
      >
        Back to workspaces
      </Link>
    </div>
  );
}

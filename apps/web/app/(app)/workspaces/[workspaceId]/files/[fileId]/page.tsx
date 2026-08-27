import { redirect } from "next/navigation";

// Per the UI spec, file descriptions are surfaced via the Description Drawer
// (a slide-over on the workspace detail page), not a standalone page —
// see docs/UI.md §4.2 and §18 ("Separate pages for every detail" is an
// anti-pattern to reject). This route exists only to avoid a dead link /
// blank page if something ever deep-links to a specific file; it forwards
// back to the workspace detail view where the drawer lives.
export default async function FileDetailRedirectPage({
  params,
}: {
  params: Promise<{ workspaceId: string; fileId: string }>;
}) {
  const { workspaceId } = await params;
  redirect(`/workspaces/${workspaceId}`);
}

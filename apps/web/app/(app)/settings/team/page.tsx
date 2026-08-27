"use client";

import { useEffect, useState } from "react";
import { UserPlus, Mail, MoreHorizontal, X } from "lucide-react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { TableSkeleton, ErrorState } from "@/components/shared/DataStates";
import { useResource } from "@/lib/data/useResource";
import {
  TEAM_ROLES,
  formatJoined,
  inviteTeamMember,
  listTeamMembers,
  removeTeamMember,
  updateTeamMemberRole,
  type TeamMember,
  type TeamRole,
} from "@/lib/data/team";
import { initialsOf } from "@/lib/data/session";
import { cn } from "@/lib/utils/cn";

type Role = TeamRole;
type Member = TeamMember;

const ROLES: readonly Role[] = TEAM_ROLES;

const initials = initialsOf;

function formatRole(role: Role): string { return role; }

export default function TeamPage() {
  const { data, status, error, retry } = useResource(listTeamMembers, []);

  // Local copy so role changes, invitations, and removals reflect immediately;
  // re-seeded whenever the server list arrives.
  const [members, setMembers] = useState<Member[]>([]);
  useEffect(() => {
    if (data) setMembers(data);
  }, [data]);

  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole]   = useState<Role>("Analyst");
  const [mutationError, setMutationError] = useState<string | null>(null);

  const activeCount  = members.filter((m) => !m.pending).length;
  const pendingCount = members.filter((m) => m.pending).length;

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    try {
      const invited = await inviteTeamMember(inviteEmail.trim(), inviteRole);
      setMembers((prev) => [...prev, invited]);
      setInviteEmail("");
      setInviteRole("Analyst");
      setShowInvite(false);
      setMutationError(null);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRoleChange = async (id: string, role: Role) => {
    const previous = members;
    setMembers((prev) => prev.map((m) => m.id === id ? { ...m, role } : m));
    try {
      await updateTeamMemberRole(id, role);
      setMutationError(null);
    } catch (err) {
      setMembers(previous);
      setMutationError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRemove = async (id: string) => {
    const previous = members;
    setMembers((prev) => prev.filter((m) => m.id !== id));
    try {
      await removeTeamMember(id);
      setMutationError(null);
    } catch (err) {
      setMembers(previous);
      setMutationError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      <SettingsCard title="Team members">
        {/* Header row */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-vera-muted">
            {status === "loading" ? (
              <span className="inline-block h-3 w-24 rounded bg-vera-border-subtle shimmer align-middle" />
            ) : (
              <>
                {activeCount} member{activeCount !== 1 ? "s" : ""}
                {pendingCount > 0 && ` · ${pendingCount} pending`}
              </>
            )}
          </p>
          <button
            onClick={() => setShowInvite((v) => !v)}
            className="vera-btn-primary text-xs py-1.5 px-3"
          >
            <UserPlus size={13} strokeWidth={1.75} />
            Invite
          </button>
        </div>

        {/* Inline invite form */}
        {showInvite && (
          <div className="mb-4 p-4 rounded-lg border border-vera-border bg-vera-border-subtle space-y-3">
            <div className="flex gap-2 items-end">
              <div className="flex-1 space-y-1">
                <label className="text-xs font-medium text-vera-ink block">Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="vera-input text-sm"
                  onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                  autoFocus
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-vera-ink block">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as Role)}
                  className="vera-input text-sm appearance-none pr-6"
                  style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238B8B9E' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\")", backgroundRepeat: "no-repeat", backgroundPosition: "right 8px center" }}
                >
                  {ROLES.filter((r) => r !== "Owner").map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setShowInvite(false); setInviteEmail(""); }}
                className="vera-btn-ghost text-xs py-1.5 px-3"
              >
                Cancel
              </button>
              <button
                onClick={handleInvite}
                disabled={!inviteEmail.trim()}
                className={cn(
                  "vera-btn-primary text-xs py-1.5 px-3",
                  !inviteEmail.trim() && "opacity-50 cursor-not-allowed"
                )}
              >
                Send invite
              </button>
            </div>
          </div>
        )}

        {/* Mutation failures — the list itself is still valid, so report inline. */}
        {mutationError && (
          <p className="text-xs text-vera-insufficient mb-3">{mutationError}</p>
        )}

        {/* Members table */}
        {status === "error" ? (
          <ErrorState error={error} onRetry={retry} />
        ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-vera-border">
                <th className="table-header pb-2 text-left">Member</th>
                <th className="table-header pb-2 text-left">Role</th>
                <th className="table-header pb-2 text-left">Joined</th>
                <th className="table-header pb-2 text-left">Actions</th>
              </tr>
            </thead>
            {status === "loading" ? (
              <TableSkeleton rows={3} cols={4} />
            ) : members.length === 0 ? (
              <tbody>
                <tr>
                  <td colSpan={4} className="py-8 text-center text-sm text-vera-muted">
                    No team members yet. Invite a colleague to get started.
                  </td>
                </tr>
              </tbody>
            ) : (
            <tbody>
              {members.map((member) => (
                <tr key={member.id} className="border-b border-vera-border-subtle last:border-0">
                  {/* Member column */}
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2.5">
                      {member.pending ? (
                        <div className="w-8 h-8 rounded-full bg-vera-border flex items-center justify-center shrink-0">
                          <Mail size={14} strokeWidth={1.5} className="text-vera-muted" />
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-vera-accent-muted border border-vera-accent/20 flex items-center justify-center shrink-0">
                          <span className="text-[11px] font-bold text-vera-accent">
                            {initials(member.name)}
                          </span>
                        </div>
                      )}
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          {member.name && (
                            <span className="text-sm font-medium text-vera-ink">{member.name}</span>
                          )}
                          {member.isYou && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-vera-accent-muted text-vera-accent font-medium">
                              You
                            </span>
                          )}
                          {member.pending && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-vera-border text-vera-muted font-medium">
                              Invited
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-vera-muted truncate">{member.email}</p>
                      </div>
                    </div>
                  </td>

                  {/* Role column */}
                  <td className="py-3 pr-4">
                    {member.isYou || member.role === "Owner" ? (
                      <span className="text-sm text-vera-muted">{formatRole(member.role)}</span>
                    ) : (
                      <select
                        value={member.role}
                        onChange={(e) => handleRoleChange(member.id, e.target.value as Role)}
                        className="text-sm text-vera-ink bg-transparent border border-vera-border rounded px-2 py-1 cursor-pointer hover:border-vera-accent transition-colors outline-none"
                      >
                        {ROLES.filter((r) => r !== "Owner").map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    )}
                  </td>

                  {/* Joined column */}
                  <td className="py-3 pr-4 text-sm text-vera-muted whitespace-nowrap">
                    {member.pending ? "—" : formatJoined(member.joinedAt)}
                  </td>

                  {/* Actions column */}
                  <td className="py-3">
                    {!member.isYou && (
                      <div className="flex items-center gap-2">
                        {member.pending && (
                          <button className="text-xs text-vera-muted hover:text-vera-ink transition-colors">
                            Resend
                          </button>
                        )}
                        <button
                          onClick={() => handleRemove(member.id)}
                          className={cn(
                            "text-xs transition-colors",
                            member.pending
                              ? "text-vera-muted hover:text-vera-insufficient"
                              : "text-vera-muted hover:text-vera-insufficient"
                          )}
                          title={member.pending ? "Revoke invitation" : "Remove member"}
                        >
                          {member.pending ? "Revoke" : "Remove"}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            )}
          </table>
        </div>
        )}
      </SettingsCard>
    </div>
  );
}

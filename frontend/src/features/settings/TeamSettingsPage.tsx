import { useQuery } from "@tanstack/react-query";
import { LoadingPage, PageFrame, SectionCard } from "../../components/ui";
import { useAuth } from "../../lib/auth";
import { liveGetWorkspaceMembers } from "../../lib/live-api";
import { isMockMode } from "../../lib/config";

export function TeamSettingsPage() {
  const { user } = useAuth();
  const { data: teamMembers, isLoading } = useQuery({
    queryKey: ["workspace-members"],
    queryFn: liveGetWorkspaceMembers,
    enabled: !isMockMode(),
  });

  const members = isMockMode()
    ? [
        { id: "user_1", userId: "user_1", name: "Alex Rivera", email: "alex@studio.io", role: "Admin", status: "Active" },
        { id: "user_2", userId: "user_2", name: "Taylor Swift", email: "taylor@studio.io", role: "Editor", status: "Active" },
        { id: "user_3", userId: "user_3", name: "Reviewer Joe", email: "joe@studio.io", role: "Reviewer", status: "Invited" },
      ]
    : (teamMembers ?? []);

  if (isLoading && !isMockMode()) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Workspace Settings"
      title="Team Members"
      description="Manage the people in your workspace. Roles restrict actions: Reviewers can only approve and comment, Editors can generate content, and Admins can manage workspace systems."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Roles active">
            <div className="inspector-list">
              <div>
                <span>Admins</span>
                <strong>{members.filter((member) => member.role === "Admin").length}</strong>
              </div>
              <div>
                <span>Editors</span>
                <strong>{members.filter((member) => member.role === "Member" || member.role === "Editor").length}</strong>
              </div>
              <div>
                <span>Reviewers</span>
                <strong>{members.filter((member) => member.role === "Reviewer").length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <div className="surface-card">
        <div className="mb-6 flex items-center justify-between gap-3">
          <h3 className="font-heading text-lg font-bold text-primary">Workspace Users</h3>
          <button className="inline-flex items-center justify-center rounded-xl border border-border-subtle bg-glass px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 hover:-translate-y-px hover:border-border-active hover:bg-glass-hover">
            Invite Member
          </button>
        </div>

        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id}>
                  <td className={member.userId === user?.id ? "font-semibold" : undefined}>
                    {member.name} {member.userId === user?.id ? "(You)" : ""}
                  </td>
                  <td className="text-secondary">{member.email}</td>
                  <td>
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                        member.role === "Admin"
                          ? "bg-primary-bg text-primary-fg"
                          : "bg-glass text-secondary"
                      }`}
                    >
                      {member.role}
                    </span>
                  </td>
                  <td className={member.status === "Active" ? "text-success" : "text-warning"}>
                    {member.status}
                  </td>
                  <td className="text-right">
                    <button className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-glass px-3 py-1.5 text-xs font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover">
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageFrame>
  );
}

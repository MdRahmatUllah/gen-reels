import React from "react";
import { PageFrame } from "../../components/ui";
import { useAuth } from "../../lib/auth";

export function TeamSettingsPage() {
  const { user } = useAuth();

  const teamMembers = [
    { id: "user_1", name: "Alex Rivera", email: "alex@studio.io", role: "Admin", status: "Active" },
    { id: "user_2", name: "Taylor Swift", email: "taylor@studio.io", role: "Editor", status: "Active" },
    { id: "user_3", name: "Reviewer Joe", email: "joe@studio.io", role: "Reviewer", status: "Invited" },
  ];

  return (
    <PageFrame
      eyebrow="Workspace Settings"
      title="Team Members"
      description="Manage the people in your workspace. Roles restrict actions: Reviewers can only approve and comment, Editors can generate content, and Admins can build brand kits."
      inspector={
        <div className="inspector-stack">
          <div className="surface-card">
            <h3 className="section-heading">Roles active</h3>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "12px" }}>
              <span className="body-copy">Admins</span>
              <strong>1</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
              <span className="body-copy">Editors</span>
              <strong>1</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
              <span className="body-copy">Reviewers</span>
              <strong>1</strong>
            </div>
          </div>
        </div>
      }
    >
      <div className="surface-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
          <h3 className="section-heading" style={{ fontSize: "16px" }}>Workspace Users</h3>
          <button className="button button--secondary">Invite Member</button>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
              <th style={{ padding: "12px", color: "var(--color-ink-lighter)", fontWeight: 500 }}>Name</th>
              <th style={{ padding: "12px", color: "var(--color-ink-lighter)", fontWeight: 500 }}>Email</th>
              <th style={{ padding: "12px", color: "var(--color-ink-lighter)", fontWeight: 500 }}>Role</th>
              <th style={{ padding: "12px", color: "var(--color-ink-lighter)", fontWeight: 500 }}>Status</th>
              <th style={{ padding: "12px", color: "var(--color-ink-lighter)", fontWeight: 500 }}></th>
            </tr>
          </thead>
          <tbody>
            {teamMembers.map((member) => (
              <tr key={member.id} style={{ borderBottom: "1px solid var(--color-border-subtle)" }}>
                <td style={{ padding: "16px 12px", fontWeight: member.id === user?.id ? 600 : 400 }}>
                  {member.name} {member.id === user?.id && "(You)"}
                </td>
                <td style={{ padding: "16px 12px", color: "var(--color-ink-lighter)" }}>{member.email}</td>
                <td style={{ padding: "16px 12px" }}>
                  <span style={{
                    display: "inline-block",
                    padding: "4px 8px",
                    background: member.role === "Admin" ? "var(--color-accent-subtle)" : "var(--color-background-raised)",
                    color: member.role === "Admin" ? "var(--color-accent)" : "var(--color-ink)",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: 500
                  }}>
                    {member.role}
                  </span>
                </td>
                <td style={{ padding: "16px 12px", color: member.status === "Active" ? "var(--color-success)" : "var(--color-warning)" }}>
                  {member.status}
                </td>
                <td style={{ padding: "16px 12px", textAlign: "right" }}>
                  <button className="button button--secondary" style={{ padding: "4px 8px" }}>Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PageFrame>
  );
}

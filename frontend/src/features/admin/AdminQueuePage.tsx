import { PageFrame, SectionCard, StatusBadge, LoadingPage } from "../../components/ui";
import { useAdminQueue, useReleaseQueueItem, useRejectQueueItem } from "../../hooks/use-admin";

export function AdminQueuePage() {
  const { data, isLoading } = useAdminQueue();
  const releaseMutation = useReleaseQueueItem();
  const rejectMutation = useRejectQueueItem();

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin queue"
      title="Operational queue desk"
      description="Review flagged items from pipeline moderation algorithms and release them back to execution."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Queue snapshot">
            <div className="inspector-list">
              <div>
                <span>Active items</span>
                <strong>{data.length}</strong>
              </div>
              <div>
                <span>Blocked jobs</span>
                <strong>{data.filter((row) => row.status === "blocked").length}</strong>
              </div>
              <div>
                <span>Retrying jobs</span>
                <strong>{data.filter((row) => row.retries > 0).length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Queue items" subtitle="The admin desk focuses on execution health, provider ownership, and stuck time">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Workspace</th>
                <th>Project</th>
                <th>Step</th>
                <th>Status</th>
                <th>Retries</th>
                <th>Provider</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.workspace}</td>
                  <td>{row.project}</td>
                  <td>{row.step}</td>
                  <td>
                    <StatusBadge status={row.status as any} />
                  </td>
                  <td>{row.retries}</td>
                  <td>{row.provider}</td>
                  <td style={{ textAlign: "right" }}>
                    {row.status === "blocked" && (
                      <div style={{ display: "inline-flex", gap: "0.5rem" }}>
                        <button
                          className="button button--secondary"
                          style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                          onClick={() => rejectMutation.mutate(row.id)}
                          disabled={rejectMutation.isPending || releaseMutation.isPending}
                        >
                          Reject
                        </button>
                        <button
                          className="button button--primary"
                          style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                          onClick={() => releaseMutation.mutate(row.id)}
                          disabled={rejectMutation.isPending || releaseMutation.isPending}
                        >
                          Release
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", color: "var(--color-ink-lighter)" }}>
                    The queue is entirely clean.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </PageFrame>
  );
}

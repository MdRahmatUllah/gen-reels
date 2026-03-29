import { LoadingPage, PageFrame, SectionCard, StatusBadge } from "../../components/ui";
import { useAdminQueue, useRejectQueueItem, useReleaseQueueItem } from "../../hooks/use-admin";

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
                <th className="text-right">Actions</th>
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
                    <StatusBadge status={row.status} />
                  </td>
                  <td>{row.retries}</td>
                  <td>{row.provider}</td>
                  <td className="text-right">
                    {row.status === "blocked" ? (
                      <div className="inline-flex gap-2">
                        <button
                          className="inline-flex items-center justify-center rounded-lg border border-border-subtle bg-glass px-3 py-1.5 text-xs font-semibold text-primary transition-all duration-200 hover:border-border-active hover:bg-glass-hover disabled:opacity-60"
                          onClick={() => rejectMutation.mutate(row.id)}
                          disabled={rejectMutation.isPending || releaseMutation.isPending}
                          type="button"
                        >
                          Reject
                        </button>
                        <button
                          className="inline-flex items-center justify-center rounded-lg bg-accent-gradient px-3 py-1.5 text-xs font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent disabled:opacity-60"
                          onClick={() => releaseMutation.mutate(row.id)}
                          disabled={rejectMutation.isPending || releaseMutation.isPending}
                          type="button"
                        >
                          Release
                        </button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
              {data.length === 0 ? (
                <tr>
                  <td className="text-center text-muted" colSpan={8}>
                    The queue is entirely clean.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </PageFrame>
  );
}

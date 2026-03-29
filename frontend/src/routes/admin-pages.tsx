import {
  useAdminQueue,
  useAdminRenders,
  useAdminWorkspaces,
  useReleaseQueueItem,
  useRejectQueueItem,
} from "../hooks/use-admin";
import { PageFrame, SectionCard, StatusBadge } from "../components/ui";

function LoadingAdminPage() {
  return (
    <PageFrame
      eyebrow="Loading"
      title="Preparing admin view"
      description="Admin workspace data is loading."
      inspector={<div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in shimmer" />}
    >
      <div className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in shimmer" />
    </PageFrame>
  );
}

export function AdminQueuePage() {
  const { data, isLoading } = useAdminQueue();
  const releaseQueueItem = useReleaseQueueItem();
  const rejectQueueItem = useRejectQueueItem();

  if (isLoading || !data) {
    return <LoadingAdminPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin queue"
      title="Operational queue desk"
      description="Workspace-admin moderation and intervention items are surfaced here with the same visual system as the rest of the app."
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
      <SectionCard title="Queue items" subtitle="The admin desk focuses on moderation holds, provider ownership, and fast intervention.">
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
                <th>Owner</th>
                <th>Age</th>
                <th>Provider</th>
                <th>Actions</th>
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
                  <td>{row.owner}</td>
                  <td>{row.age}</td>
                  <td>{row.provider}</td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded-md border border-emerald-700/60 bg-emerald-950/30 px-3 py-1.5 text-xs font-medium text-emerald-200 transition-colors hover:bg-emerald-900/50 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={releaseQueueItem.isPending || rejectQueueItem.isPending}
                        onClick={() => releaseQueueItem.mutate(row.id)}
                      >
                        Release
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-rose-700/60 bg-rose-950/40 px-3 py-1.5 text-xs font-medium text-rose-200 transition-colors hover:bg-rose-900/60 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={releaseQueueItem.isPending || rejectQueueItem.isPending}
                        onClick={() => rejectQueueItem.mutate(row.id)}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function AdminWorkspacesPage() {
  const { data, isLoading } = useAdminWorkspaces();

  if (isLoading || !data) {
    return <LoadingAdminPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin workspaces"
      title="Workspace health"
      description="This view is trimmed to the current admin-accessible workspace until broader cross-workspace backend summaries are introduced."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Workspace health">
            <div className="inspector-list">
              <div>
                <span>Total workspaces</span>
                <strong>{data.length}</strong>
              </div>
              <div>
                <span>High load</span>
                <strong>{data.filter((row) => row.health !== "Healthy").length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Workspace table" subtitle="Operational visibility stays dense but readable via tonal rows instead of borders">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Plan</th>
                <th>Seats</th>
                <th>Credits</th>
                <th>Render load</th>
                <th>Health</th>
                <th>Renewal</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.name}</td>
                  <td>{row.plan}</td>
                  <td>{row.seats}</td>
                  <td>{row.creditsRemaining}</td>
                  <td>{row.renderLoad}</td>
                  <td>
                    <StatusBadge status={row.health} />
                  </td>
                  <td>{row.renewalDate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </PageFrame>
  );
}

export function AdminRendersPage() {
  const { data, isLoading } = useAdminRenders();

  if (isLoading || !data) {
    return <LoadingAdminPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin renders"
      title="Render health"
      description="An operations-first surface for active workspace render failures, queue state, and backend-reported cost signals."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Incident bias">
            <div className="inspector-list">
              <div>
                <span>Failed renders</span>
                <strong>{data.filter((row) => row.status === "failed").length}</strong>
              </div>
              <div>
                <span>Blocked renders</span>
                <strong>{data.filter((row) => row.status === "blocked").length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Render fleet table" subtitle="The admin desk keeps root-cause context close to the queue state">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Project</th>
                <th>Workspace</th>
                <th>Status</th>
                <th>Provider</th>
                <th>Cost</th>
                <th>Stuck</th>
                <th>Issue</th>
                <th>Snapshot</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.project}</td>
                  <td>{row.workspace}</td>
                  <td>
                    <StatusBadge status={row.status} />
                  </td>
                  <td>{row.provider}</td>
                  <td>{row.cost}</td>
                  <td>{row.stuckFor}</td>
                  <td>{row.issue}</td>
                  <td>{row.snapshot}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </PageFrame>
  );
}

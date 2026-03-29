import { PageFrame, SectionCard, StatusBadge, LoadingPage } from "../../components/ui";
import { useAdminRenders } from "../../hooks/use-admin";

export function AdminRendersPage() {
  const { data, isLoading } = useAdminRenders();

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin renders"
      title="Cross-workspace render health"
      description="An operations-first surface for cost, provider choice, consistency snapshot provenance, and failure triage."
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
                    <StatusBadge status={row.status as any} />
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

import { PageFrame, SectionCard, StatusBadge, LoadingPage } from "../../components/ui";
import { useAdminWorkspaces } from "../../hooks/use-admin";

export function AdminWorkspacesPage() {
  const { data, isLoading } = useAdminWorkspaces();

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin workspaces"
      title="Workspace fleet"
      description="A mock control surface for plan health, seat counts, and render load visibility across customers."
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
                    <StatusBadge status={row.health as any} />
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

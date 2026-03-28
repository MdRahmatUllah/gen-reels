import { useQuery } from "@tanstack/react-query";

import {
  getAdminQueue,
  getAdminRenders,
  getAdminWorkspaces,
} from "../lib/mock-api";
import { PageFrame, SectionCard, StatusBadge } from "../components/ui";

function LoadingAdminPage() {
  return (
    <PageFrame
      eyebrow="Loading"
      title="Preparing admin view"
      description="Admin mock data is loading."
      inspector={<div className="surface-card shimmer surface-card--loading" />}
    >
      <div className="surface-card shimmer surface-card--loading" />
    </PageFrame>
  );
}

export function AdminQueuePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-queue"],
    queryFn: getAdminQueue,
  });

  if (isLoading || !data) {
    return <LoadingAdminPage />;
  }

  return (
    <PageFrame
      eyebrow="Admin queue"
      title="Operational queue desk"
      description="Admin routes are deliberately separate from the workspace navigation but keep the same visual system and layout logic."
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
                <th>Owner</th>
                <th>Age</th>
                <th>Provider</th>
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
  const { data, isLoading } = useQuery({
    queryKey: ["admin-workspaces"],
    queryFn: getAdminWorkspaces,
  });

  if (isLoading || !data) {
    return <LoadingAdminPage />;
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
  const { data, isLoading } = useQuery({
    queryKey: ["admin-renders"],
    queryFn: getAdminRenders,
  });

  if (isLoading || !data) {
    return <LoadingAdminPage />;
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

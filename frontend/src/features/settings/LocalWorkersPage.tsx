import { PageFrame, SectionCard, StatusBadge, LoadingPage } from "../../components/ui";
import { useLocalWorkers } from "../../hooks/use-providers";

export function LocalWorkersPage() {
  const { data: workers, isLoading } = useLocalWorkers();

  if (isLoading) return <LoadingPage />;

  return (
    <PageFrame 
      eyebrow="Settings" 
      title="Local Workers" 
      description="Monitor registered edge devices and hardware nodes reporting into this workspace."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Hybrid Execution">
            <p className="body-copy">
              If an executing prompt's required capabilities match an online Local Worker, the orchestration engine will detour the execution vector to the edge device, bypassing hosted usage billing entirely.
            </p>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Active Fleet" subtitle="Workers available for execution routing when capabilities match the prompt modality.">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>Node Name</th>
                <th>Status</th>
                <th>Capabilities</th>
                <th>Last Heartbeat</th>
              </tr>
            </thead>
            <tbody>
              {workers?.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", color: "var(--color-ink-lighter)" }}>No local workers registered.</td>
                </tr>
              )}
              {workers?.map((w) => (
                <tr key={w.id}>
                  <td><strong>{w.name}</strong><div style={{ fontSize: "10px", color: "var(--color-ink-lighter)", marginTop: "2px" }}>ID: {w.id}</div></td>
                  <td>
                    <StatusBadge status={w.status === "online" ? "active" : "offline"} />
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", maxWidth: "250px" }}>
                      {w.capabilities.orderedReferenceImages && <span className="approval-badge" style={{ fontSize: "10px", padding: "2px 4px" }}>Images (Reference)</span>}
                      {w.capabilities.videoFrames && <span className="approval-badge" style={{ fontSize: "10px", padding: "2px 4px" }}>Video</span>}
                      {w.capabilities.localTTS && <span className="approval-badge" style={{ fontSize: "10px", padding: "2px 4px" }}>TTS</span>}
                    </div>
                  </td>
                  <td style={{ color: "var(--color-ink-lighter)" }}>{new Date(w.lastHeartbeat).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
      
      <SectionCard title="Architecture Note" subtitle="How this works">
        <p className="body-copy">
          To register a new local worker, download the agent package, authorize using your workspace token, and launch the daemon. The agent connects to our centralized orchestration queue over WebSockets via egress only, requiring no firewall port-forwarding modifications on your end.
        </p>
      </SectionCard>
    </PageFrame>
  );
}

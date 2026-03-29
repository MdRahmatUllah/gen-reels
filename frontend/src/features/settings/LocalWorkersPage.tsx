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
        <div className="flex flex-col gap-4">
          <SectionCard title="Hybrid Execution">
            <p className="text-sm text-slate-300 leading-relaxed">
              If an executing prompt's required capabilities match an online Local Worker, the orchestration engine will detour the execution vector to the edge device, bypassing hosted usage billing entirely.
            </p>
          </SectionCard>
        </div>
      }
    >
      <SectionCard title="Active Fleet" subtitle="Workers available for execution routing when capabilities match the prompt modality.">
        <div className="overflow-x-auto rounded-lg border border-slate-800/60 bg-slate-900/40">
          <table className="w-full text-left text-sm text-slate-300">
            <thead>
              <tr>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Node Name</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Capabilities</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody>
              {workers?.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-sm text-slate-500">No local workers registered.</td>
                </tr>
              )}
              {workers?.map((w) => (
                <tr key={w.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="border-b border-slate-800/50 px-4 py-3">
                    <div className="font-semibold text-slate-200">{w.name}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">ID: {w.id}</div>
                  </td>
                  <td className="border-b border-slate-800/50 px-4 py-3">
                    <StatusBadge status={w.status === "online" ? "active" : "offline"} />
                  </td>
                  <td className="border-b border-slate-800/50 px-4 py-3">
                    <div className="flex flex-wrap gap-1.5 max-w-[250px]">
                      {w.capabilities.orderedReferenceImages && <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-300 border border-slate-700/50">Images (Reference)</span>}
                      {w.capabilities.videoFrames && <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-300 border border-slate-700/50">Video</span>}
                      {w.capabilities.localTTS && <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-300 border border-slate-700/50">TTS</span>}
                    </div>
                  </td>
                  <td className="border-b border-slate-800/50 px-4 py-3 text-xs text-slate-400">{new Date(w.lastHeartbeat).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
      
      <SectionCard title="Architecture Note" subtitle="How this works">
        <p className="text-sm text-slate-300 leading-relaxed">
          To register a new local worker, download the agent package, authorize using your workspace token, and launch the daemon. The agent connects to our centralized orchestration queue over WebSockets via egress only, requiring no firewall port-forwarding modifications on your end.
        </p>
      </SectionCard>
    </PageFrame>
  );
}

import { Link } from "react-router-dom";
import {
  PageFrame,
  SectionCard,
  StatusBadge,
  MetricCard,
  EmptyState,
  LoadingPage,
} from "../../components/ui";
import { useParams } from "react-router-dom";
import { useProject } from "../../hooks/use-projects";
import { useExports } from "../../hooks/use-exports";
import type { ExportArtifact } from "../../types/domain";

function formatDuration(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s < 10 ? "0" : ""}${s}s`;
}

function isVideoUrl(url: string) {
  return url.startsWith("http") || url.startsWith("/");
}

function ExportCard({ artifact }: { artifact: ExportArtifact }) {
  return (
    <div className="artifact-card">
      {isVideoUrl(artifact.destination) ? (
        <video
          controls
          playsInline
          src={artifact.destination}
          style={{ width: "100%", borderRadius: "10px", display: "block", background: "#000" }}
        />
      ) : (
        <div className="h-32 rounded-lg border border-border-subtle bg-glass/50 flex items-center justify-center text-xs text-muted">
          {artifact.format}
        </div>
      )}
      <div className="artifact-card__meta">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={artifact.status} />
          <span>{formatDuration(artifact.durationSec)}</span>
        </div>
        <p>
          {artifact.subtitles ? "Subtitles on" : "Subtitles off"} ·{" "}
          {artifact.musicBed ? "Music bed on" : "Music bed off"}
        </p>
        {isVideoUrl(artifact.destination) && (
          <a
            href={artifact.destination}
            download="export.mp4"
            className="inline-flex items-center gap-1.5 mt-1 rounded-lg bg-accent-gradient px-3 py-1.5 text-xs font-semibold text-on-accent shadow-sm hover:shadow-accent"
          >
            Download MP4
          </a>
        )}
      </div>
    </div>
  );
}

export function ExportsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading: projectLoading } = useProject(projectId || "");
  const { data: exportsData, isLoading: exportsLoading } = useExports(project?.id || "");

  if (projectLoading || exportsLoading || !project) {
    return <LoadingPage />;
  }

  const latestExport = exportsData && exportsData.length > 0 ? exportsData[0] : null;

  return (
    <PageFrame
      eyebrow="Export library"
      title={`${project.title} exports`}
      description="Final exports expose delivery metadata, loudness outcomes, and channel-specific readiness so release decisions feel operational, not guessy."
      actions={
        <>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px" to={`/app/projects/${project.id}/renders`}>
            Back to renders
          </Link>
          <Link className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px" to={`/app/projects/${project.id}/brief`}>
            Review brief context
          </Link>
        </>
      }
      inspector={
        latestExport ? (
          <div className="inspector-stack">
            <SectionCard title="Publish checklist">
              <div className="check-list">
                <div className="check-item">
                  <StatusBadge status={latestExport.subtitles ? "approved" : "review"} />
                  <div>
                    <strong>Subtitle coverage</strong>
                    <p>{latestExport.subtitles ? "Burn-in enabled" : "No subtitles on this export"}</p>
                  </div>
                </div>
                <div className="check-item">
                  <StatusBadge status={latestExport.musicBed ? "approved" : "review"} />
                  <div>
                    <strong>Music continuity</strong>
                    <p>{latestExport.musicBed ? "Music bed delivered with fade" : "No music bed attached"}</p>
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Master metrics">
              <div className="inspector-list">
                <div>
                  <span>Integrated loudness</span>
                  <strong>{latestExport.integratedLufs} LUFS</strong>
                </div>
                <div>
                  <span>True peak</span>
                  <strong>{latestExport.truePeak} dBTP</strong>
                </div>
                <div>
                  <span>Format</span>
                  <strong>{latestExport.format}</strong>
                </div>
                <div>
                  <span>Destination</span>
                  <strong>{latestExport.destination}</strong>
                </div>
              </div>
            </SectionCard>
          </div>
        ) : (
          <div className="inspector-stack">
            <EmptyState title="No exports" description="Complete a render to view exports." />
          </div>
        )
      }
    >
      {latestExport ? (
        <>
          <SectionCard className="surface-card--hero" title={latestExport.name} subtitle="Latest master output">
            <div className="hero-grid">
              {isVideoUrl(latestExport.destination) ? (
                <div className="flex flex-col gap-3">
                  <video
                    controls
                    playsInline
                    src={latestExport.destination}
                    style={{ width: "100%", maxWidth: "360px", borderRadius: "12px", display: "block", background: "#000" }}
                  />
                  <a
                    href={latestExport.destination}
                    download="export.mp4"
                    className="inline-flex items-center gap-2 rounded-xl bg-accent-gradient px-4 py-2 text-sm font-semibold text-on-accent shadow-sm hover:shadow-accent self-start"
                  >
                    Download MP4
                  </a>
                </div>
              ) : (
                <div className="h-48 rounded-xl border border-border-subtle bg-glass/50 flex items-center justify-center text-sm text-muted">
                  Processing…
                </div>
              )}
              <div className="metric-column">
                <MetricCard label="Duration" value={formatDuration(latestExport.durationSec)} detail="Final export length" tone="primary" />
                <MetricCard label="File size" value={`${latestExport.sizeMb} MB`} detail="Fast-start optimized" tone="neutral" />
                {latestExport.createdAt && (
                  <MetricCard label="Created" value={latestExport.createdAt} detail="Latest delivered artifact" tone="success" />
                )}
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Export library" subtitle="Cards stay visual while metadata keeps the operational details close">
            <div className="artifact-grid">
              {exportsData?.map((artifact) => (
                <ExportCard key={artifact.id} artifact={artifact} />
              ))}
            </div>
          </SectionCard>
        </>
      ) : (
        <EmptyState 
           title="No Exports Yet"
           description="Your project has no successful exports. Go to the Renders tab to start a new composition pipeline."
        />
      )}
    </PageFrame>
  );
}

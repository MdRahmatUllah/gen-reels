import { Link } from "react-router-dom";
import {
  PageFrame,
  SectionCard,
  StatusBadge,
  MetricCard,
  MediaFrame,
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

function ExportCard({ artifact }: { artifact: ExportArtifact }) {
  return (
    <div className="artifact-card">
      {artifact.downloadUrl ? (
        <video
          src={artifact.downloadUrl}
          controls
          playsInline
          style={{ width: "100%", borderRadius: "8px", background: "#000", maxHeight: "320px" }}
        />
      ) : (
        <MediaFrame
          label={artifact.name}
          meta={`${artifact.ratio} · ${artifact.format}`}
          gradient={artifact.gradient}
        />
      )}
      <div className="artifact-card__meta">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={artifact.status} />
          <span>{formatDuration(artifact.durationSec)}</span>
          {artifact.sizeMb > 0 && <span>{artifact.sizeMb} MB</span>}
        </div>
        {artifact.downloadUrl && (
          <a
            href={artifact.downloadUrl}
            download={artifact.name}
            className="inline-flex items-center justify-center gap-2 min-h-[2.2rem] px-3 py-1 rounded-md font-semibold text-xs transition-all duration-200 cursor-pointer bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
          >
            Download MP4
          </a>
        )}
        <p>
          {artifact.subtitles ? "Subtitles on" : "Subtitles off"} ·{" "}
          {artifact.musicBed ? "Music bed on" : "Music bed off"}
        </p>
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
              {latestExport.downloadUrl ? (
                <div style={{ position: "relative" }}>
                  <video
                    src={latestExport.downloadUrl}
                    controls
                    playsInline
                    style={{ width: "100%", borderRadius: "10px", background: "#000", maxHeight: "480px", display: "block" }}
                  />
                </div>
              ) : (
                <MediaFrame
                  label={latestExport.name}
                  meta={`${latestExport.ratio} · ${latestExport.format}`}
                  gradient={latestExport.gradient}
                  aspect="wide"
                />
              )}
              <div className="metric-column">
                <MetricCard label="Duration" value={formatDuration(latestExport.durationSec)} detail="Final export length" tone="primary" />
                {latestExport.sizeMb > 0 && (
                  <MetricCard label="File size" value={`${latestExport.sizeMb} MB`} detail="Fast-start optimized" tone="neutral" />
                )}
                {latestExport.createdAt && (
                  <MetricCard label="Created" value={latestExport.createdAt} detail="Latest delivered artifact" tone="success" />
                )}
                {latestExport.downloadUrl && (
                  <a
                    href={latestExport.downloadUrl}
                    download={latestExport.name}
                    className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"
                  >
                    Download final video
                  </a>
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

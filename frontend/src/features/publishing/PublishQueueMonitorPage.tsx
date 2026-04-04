import { PageFrame, SectionCard } from "../../components/ui";
import { usePublishJobs } from "../../hooks/use-youtube-publishing";
import { PublishingEmptyState, PublishingLiveModeNotice, PublishingMetric, StatusBadge, formatTimestamp } from "./shared";

export function PublishQueueMonitorPage() {
  const { data: jobs = [], isLoading, error } = usePublishJobs();

  return (
    <PageFrame
      eyebrow="Publishing"
      title="Publish Queue Monitor"
      description="Track scheduled, queued, publishing, published, and failed YouTube publish jobs with their assigned channel, timestamps, and latest backend error details."
      inspector={
        <div className="grid gap-4">
          <PublishingMetric label="Queued" value={String(jobs.filter((job) => job.status === "queued").length)} detail="Ready for worker pickup." />
          <PublishingMetric label="Publishing" value={String(jobs.filter((job) => job.status === "publishing").length)} detail="Currently uploading with resumable chunks." />
          <PublishingMetric label="Failed" value={String(jobs.filter((job) => job.status === "failed").length)} detail="Permanent validation failures or exhausted retries." />
        </div>
      }
    >
      <PublishingLiveModeNotice />
      {error ? (
        <SectionCard title="Load Error">
          <p className="text-sm text-error">{error instanceof Error ? error.message : "Unable to load publish jobs."}</p>
        </SectionCard>
      ) : null}
      <SectionCard
        title="Publish Jobs"
        subtitle="Immediate jobs upload right away. Future scheduled jobs are also uploaded immediately to YouTube as private scheduled videos, while older local-only scheduled jobs are still promoted by beat when they become due."
      >
        {isLoading ? (
          <p className="text-sm text-secondary">Loading publish jobs…</p>
        ) : jobs.length === 0 ? (
          <PublishingEmptyState
            title="No publish jobs yet"
            description="Schedule a video or publish one immediately to start filling the queue monitor."
          />
        ) : (
          <div className="grid gap-4">
            {jobs.map((job) => (
              <article key={job.id} className="rounded-2xl border border-border-card bg-card p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="font-heading text-lg font-bold text-primary">{job.original_file_name ?? job.id}</h3>
                      <StatusBadge status={job.status} />
                    </div>
                    <p className="mt-2 text-sm text-secondary">{job.channel_title ?? "Unknown channel"}</p>
                  </div>
                  <div className="text-right text-sm text-secondary">
                    <p>Created {formatTimestamp(job.created_at)}</p>
                    <p>Scheduled {formatTimestamp(job.scheduled_publish_at)}</p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-secondary">
                  <span className="rounded-full bg-glass px-3 py-1">Mode: {job.publish_mode}</span>
                  <span className="rounded-full bg-glass px-3 py-1">Visibility: {job.visibility}</span>
                  <span className="rounded-full bg-glass px-3 py-1">Attempts: {job.attempt_count}</span>
                  <span className="rounded-full bg-glass px-3 py-1">Progress: {job.last_progress_percent ?? 0}%</span>
                </div>
                {job.error_message ? <p className="mt-4 text-sm text-error">{job.error_message}</p> : null}
                {job.youtube_video_url ? (
                  <a className="mt-4 inline-flex text-sm font-semibold text-accent" href={job.youtube_video_url} target="_blank" rel="noreferrer">
                    Open YouTube video
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </SectionCard>
    </PageFrame>
  );
}

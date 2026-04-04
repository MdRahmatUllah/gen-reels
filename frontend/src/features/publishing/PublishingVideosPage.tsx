import { useMemo, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import { PageFrame, SectionCard } from "../../components/ui";
import { useGeneratePublishingMetadata, usePublishingVideos, useUploadPublishingVideo, useYouTubeAccounts } from "../../hooks/use-youtube-publishing";
import { PublishingEmptyState, PublishingLiveModeNotice, PublishingMetric, StatusBadge, formatDurationMs, formatFileSize, formatTimestamp } from "./shared";

export function PublishingVideosPage() {
  const { data: videos = [], isLoading, error } = usePublishingVideos();
  const { data: accounts = [] } = useYouTubeAccounts();
  const uploadMutation = useUploadPublishingVideo();
  const generateMutation = useGeneratePublishingMetadata();
  const [uploadError, setUploadError] = useState<string | null>(null);

  const summary = useMemo(() => {
    return {
      total: videos.length,
      ready: videos.filter((video) => video.status === "metadata_ready").length,
      scheduled: videos.filter((video) => video.status === "scheduled").length,
      failed: videos.filter((video) => video.status === "failed").length,
    };
  }, [videos]);

  async function handleUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.currentTarget.value = "";
    if (!file) {
      return;
    }
    setUploadError(null);
    try {
      await uploadMutation.mutateAsync(file);
    } catch (requestError) {
      setUploadError(requestError instanceof Error ? requestError.message : "Video upload failed.");
    }
  }

  return (
    <PageFrame
      eyebrow="Publishing"
      title="Video Library And Processing"
      description="Upload videos into the platform first, let Whisper and the metadata worker process them, then review the generated YouTube metadata before publishing."
      actions={
        <label className="rounded-full border border-border-active bg-primary-bg px-4 py-2 text-sm font-semibold text-primary">
          <input className="hidden" type="file" accept="video/*" onChange={(event) => void handleUploadChange(event)} />
          {uploadMutation.isPending ? "Uploading..." : "Upload Video"}
        </label>
      }
      inspector={
        <div className="grid gap-4">
          <PublishingMetric label="Videos" value={String(summary.total)} detail="Uploaded into the publishing pipeline." />
          <PublishingMetric label="Metadata Ready" value={String(summary.ready)} detail="Ready for review and approval." />
          <PublishingMetric label="Scheduled" value={String(summary.scheduled)} detail="Already assigned to a future YouTube slot." />
          <PublishingMetric label="Failed" value={String(summary.failed)} detail="Need another generation attempt or a source fix." />
        </div>
      }
    >
      <PublishingLiveModeNotice />
      {uploadError ? (
        <SectionCard title="Upload Error">
          <p className="text-sm text-error">{uploadError}</p>
        </SectionCard>
      ) : null}
      {error ? (
        <SectionCard title="Load Error">
          <p className="text-sm text-error">{error instanceof Error ? error.message : "Unable to load videos."}</p>
        </SectionCard>
      ) : null}
      <SectionCard
        title="Publishing Queue Inputs"
        subtitle="Statuses update live while background jobs transcribe voiceover, generate YouTube metadata, and prepare videos for scheduled publishing."
      >
        {isLoading ? (
          <p className="text-sm text-secondary">Loading videos…</p>
        ) : videos.length === 0 ? (
          <PublishingEmptyState
            title="No uploaded videos yet"
            description="Upload a video to start transcription with the local Whisper small model and generate reviewable YouTube metadata."
          />
        ) : (
          <div className="grid gap-4">
            {videos.map((video) => {
              const account = accounts.find((item) => item.id === video.youtube_account_id);
              return (
                <article key={video.id} className="rounded-2xl border border-border-card bg-card p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-heading text-lg font-bold text-primary">{video.original_file_name}</h3>
                        <StatusBadge status={video.status} />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-secondary">
                        <span className="rounded-full bg-glass px-3 py-1">Uploaded: {formatTimestamp(video.created_at)}</span>
                        <span className="rounded-full bg-glass px-3 py-1">Size: {formatFileSize(video.size_bytes)}</span>
                        <span className="rounded-full bg-glass px-3 py-1">Duration: {formatDurationMs(video.duration_ms)}</span>
                        <span className="rounded-full bg-glass px-3 py-1">
                          Target: {account?.channel_title ?? "Not selected"}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="rounded-full border border-border-subtle px-3 py-1.5 text-xs font-semibold text-primary transition hover:border-border-active"
                        onClick={() => generateMutation.mutate(video.id)}
                        type="button"
                        disabled={generateMutation.isPending}
                      >
                        Regenerate Metadata
                      </button>
                      <Link
                        className="rounded-full border border-border-active bg-primary-bg px-3 py-1.5 text-xs font-semibold text-primary"
                        to={`/app/publishing/videos/${video.id}/review`}
                      >
                        Review Metadata
                      </Link>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-xl border border-border-subtle bg-glass p-3">
                      <p className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Transcript</p>
                      <p className="mt-2 line-clamp-4 text-sm leading-6 text-secondary">
                        {video.transcript?.transcript_text ?? "Transcript not available yet."}
                      </p>
                    </div>
                    <div className="rounded-xl border border-border-subtle bg-glass p-3">
                      <p className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Approved Title</p>
                      <p className="mt-2 text-sm leading-6 text-secondary">
                        {video.approved_metadata_version?.title ??
                          video.metadata_versions[0]?.recommended_title ??
                          "Metadata is still processing."}
                      </p>
                      {video.processing_error_message ? (
                        <p className="mt-3 text-sm text-error">{video.processing_error_message}</p>
                      ) : null}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </SectionCard>
    </PageFrame>
  );
}

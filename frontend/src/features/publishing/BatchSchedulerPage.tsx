import { useEffect, useMemo, useState } from "react";

import { PageFrame, SectionCard } from "../../components/ui";
import { useBatchSchedulePublishingVideos, usePublishSchedules, usePublishingVideos, useYouTubeAccounts } from "../../hooks/use-youtube-publishing";
import type { BatchScheduleAssignment, PublishingVideo } from "../../types/youtube";
import { PublishingEmptyState, PublishingLiveModeNotice, PublishingMetric, StatusBadge, formatTimestamp } from "./shared";

function schedulableVideos(videos: PublishingVideo[]): PublishingVideo[] {
  return videos.filter((video) => {
    return video.approved_metadata_version !== null && !["publishing", "published", "transcribing", "uploaded"].includes(video.status);
  });
}

export function BatchSchedulerPage() {
  const { data: accounts = [] } = useYouTubeAccounts();
  const { data: schedules = [] } = usePublishSchedules();
  const { data: videos = [], isLoading, error } = usePublishingVideos();
  const batchMutation = useBatchSchedulePublishingVideos();
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([]);
  const [previewAssignments, setPreviewAssignments] = useState<BatchScheduleAssignment[]>([]);

  useEffect(() => {
    if (!selectedAccountId && accounts[0]?.id) {
      setSelectedAccountId(accounts[0].id);
    }
  }, [accounts, selectedAccountId]);

  const candidates = useMemo(() => schedulableVideos(videos), [videos]);
  const selectedSchedule = schedules.find((schedule) => schedule.youtube_account_id === selectedAccountId) ?? null;

  async function previewSlots() {
    const result = await batchMutation.mutateAsync({
      youtube_account_id: selectedAccountId,
      video_ids: selectedVideoIds,
      preview_only: true,
    });
    setPreviewAssignments(result.assignments);
  }

  async function confirmBatchSchedule() {
    const result = await batchMutation.mutateAsync({
      youtube_account_id: selectedAccountId,
      video_ids: selectedVideoIds,
      preview_only: false,
    });
    setPreviewAssignments(result.assignments);
  }

  return (
    <PageFrame
      eyebrow="Publishing"
      title="Batch Scheduler"
      description="Pick a target YouTube account, preview future slot assignments, and batch schedule multiple approved videos into the next free daily publish windows."
      inspector={
        <div className="grid gap-4">
          <PublishingMetric label="Candidates" value={String(candidates.length)} detail="Approved videos ready for scheduling." />
          <PublishingMetric label="Selected" value={String(selectedVideoIds.length)} detail="Videos queued for the preview calculation." />
          <PublishingMetric label="Schedule" value={selectedSchedule ? selectedSchedule.timezone_name : "Missing"} detail="A per-account schedule is required before batch assignment." />
        </div>
      }
    >
      <PublishingLiveModeNotice />
      {error ? (
        <SectionCard title="Load Error">
          <p className="text-sm text-error">{error instanceof Error ? error.message : "Unable to load videos."}</p>
        </SectionCard>
      ) : null}
      <SectionCard
        title="Batch Slot Assignment"
        subtitle="The preview comes from the backend scheduler, which accounts for existing future jobs and returns the next free UTC slots for the selected account."
      >
        {isLoading ? (
          <p className="text-sm text-secondary">Loading batch scheduling candidates…</p>
        ) : candidates.length === 0 ? (
          <PublishingEmptyState
            title="No schedulable videos"
            description="Approve metadata for at least one video before using the batch scheduler."
          />
        ) : (
          <div className="grid gap-5">
            <label className="flex flex-col gap-2">
              <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Target Account</span>
              <select
                className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                value={selectedAccountId}
                onChange={(event) => setSelectedAccountId(event.target.value)}
              >
                <option value="">Choose an account</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.channel_title}
                  </option>
                ))}
              </select>
            </label>

            {!selectedSchedule ? (
              <p className="text-sm text-warning">Create a daily schedule for the selected account before previewing batch slots.</p>
            ) : null}

            <div className="grid gap-3">
              {candidates.map((video) => {
                const checked = selectedVideoIds.includes(video.id);
                return (
                  <label key={video.id} className="flex items-start gap-3 rounded-2xl border border-border-card bg-card p-4">
                    <input
                      checked={checked}
                      onChange={(event) =>
                        setSelectedVideoIds((current) =>
                          event.target.checked ? [...current, video.id] : current.filter((item) => item !== video.id),
                        )
                      }
                      type="checkbox"
                      className="mt-1 h-4 w-4"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-primary">{video.original_file_name}</h3>
                        <StatusBadge status={video.status} />
                      </div>
                      <p className="mt-2 text-sm text-secondary">
                        {video.approved_metadata_version?.title ?? video.metadata_versions[0]?.recommended_title ?? "No approved title"}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                className="rounded-full border border-border-subtle px-4 py-2 text-sm font-semibold text-primary"
                onClick={() => void previewSlots()}
                type="button"
                disabled={!selectedAccountId || selectedVideoIds.length === 0 || !selectedSchedule || batchMutation.isPending}
              >
                Preview Assigned Slots
              </button>
              <button
                className="rounded-full border border-border-active bg-primary-bg px-4 py-2 text-sm font-semibold text-primary"
                onClick={() => void confirmBatchSchedule()}
                type="button"
                disabled={!selectedAccountId || selectedVideoIds.length === 0 || !selectedSchedule || batchMutation.isPending}
              >
                Confirm Batch Schedule
              </button>
              {batchMutation.error ? (
                <p className="self-center text-sm text-error">
                  {batchMutation.error instanceof Error ? batchMutation.error.message : "Batch scheduling failed."}
                </p>
              ) : null}
            </div>
          </div>
        )}
      </SectionCard>

      {previewAssignments.length > 0 ? (
        <SectionCard title="Previewed Future Publish Times" subtitle="Review the next free future assignments before confirming.">
          <div className="grid gap-3">
            {previewAssignments.map((assignment) => (
              <div key={`${assignment.video_id}-${assignment.publish_at_utc}`} className="rounded-2xl border border-border-subtle bg-glass p-4">
                <p className="font-semibold text-primary">{assignment.original_file_name}</p>
                <p className="mt-2 text-sm text-secondary">{assignment.publish_at_local_label}</p>
                <p className="mt-1 text-xs text-muted">UTC: {formatTimestamp(assignment.publish_at_utc)}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}
    </PageFrame>
  );
}

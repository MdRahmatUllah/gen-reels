import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { PageFrame, SectionCard } from "../../components/ui";
import { useApprovePublishingMetadata, usePublishingVideo, useSchedulePublishingVideo, useYouTubeAccounts } from "../../hooks/use-youtube-publishing";
import type { PublishVisibility } from "../../types/youtube";
import { PublishingEmptyState, PublishingLiveModeNotice, StatusBadge, formatTimestamp } from "./shared";

type PickerInput = HTMLInputElement & { showPicker?: () => void };

function getDefaultScheduleDateTime(): Date {
  const next = new Date(Date.now() + 15 * 60 * 1000);
  const roundedMinutes = Math.ceil(next.getMinutes() / 15) * 15;
  if (roundedMinutes >= 60) {
    next.setHours(next.getHours() + 1, 0, 0, 0);
  } else {
    next.setMinutes(roundedMinutes, 0, 0);
  }
  return next;
}

function formatDateInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatTimeInputValue(value: Date): string {
  const hours = String(value.getHours()).padStart(2, "0");
  const minutes = String(value.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function buildScheduledPublishAt(dateValue: string, timeValue: string): Date | null {
  if (!dateValue || !timeValue) {
    return null;
  }
  const [yearText, monthText, dayText] = dateValue.split("-");
  const [hourText, minuteText] = timeValue.split(":");
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if ([year, month, day, hour, minute].some((value) => Number.isNaN(value))) {
    return null;
  }
  const scheduledAt = new Date(year, month - 1, day, hour, minute, 0, 0);
  return Number.isNaN(scheduledAt.getTime()) ? null : scheduledAt;
}

export function VideoMetadataReviewPage() {
  const { videoId = "" } = useParams();
  const { data: video, isLoading, error } = usePublishingVideo(videoId);
  const { data: accounts = [] } = useYouTubeAccounts();
  const approveMutation = useApprovePublishingMetadata(videoId);
  const scheduleMutation = useSchedulePublishingVideo(videoId);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tagsText, setTagsText] = useState("");
  const [hookSummary, setHookSummary] = useState("");
  const [youtubeAccountId, setYouTubeAccountId] = useState<string>("");
  const [visibility, setVisibility] = useState<PublishVisibility>("public");
  const [isScheduleFormOpen, setIsScheduleFormOpen] = useState(false);
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("");
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const dateInputRef = useRef<HTMLInputElement | null>(null);

  const sourceMetadata = useMemo(() => {
    return video?.approved_metadata_version ?? video?.metadata_versions[0] ?? null;
  }, [video]);
  const hasApprovedMetadata = Boolean(video?.approved_metadata_version_id);
  const canRunPublishAction = hasApprovedMetadata && Boolean(youtubeAccountId) && !scheduleMutation.isPending;
  const publishActionMessage = !hasApprovedMetadata
    ? "Approve metadata below to enable scheduling and publishing."
    : !youtubeAccountId
      ? "Choose a connected YouTube account to continue."
      : scheduleMutation.isPending
        ? "Publishing action in progress..."
        : null;
  const primaryActionButtonClassName =
    "rounded-full border border-border-active bg-primary-bg px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 cursor-pointer hover:-translate-y-px hover:border-border-active disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0";
  const secondaryActionButtonClassName =
    "rounded-full border border-border-subtle px-4 py-2 text-sm font-semibold text-primary transition-all duration-200 cursor-pointer hover:-translate-y-px hover:border-border-active disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0";

  useEffect(() => {
    if (!video || !sourceMetadata) {
      return;
    }
    setTitle(sourceMetadata.title || sourceMetadata.recommended_title);
    setDescription(sourceMetadata.description);
    setTagsText(sourceMetadata.tags.join(", "));
    setHookSummary(sourceMetadata.hook_summary ?? "");
    setYouTubeAccountId(
      video.youtube_account_id ?? accounts.find((account) => account.is_default)?.id ?? accounts[0]?.id ?? "",
    );
  }, [accounts, sourceMetadata, video]);

  async function handleApprove() {
    if (!sourceMetadata) {
      return;
    }
    await approveMutation.mutateAsync({
      metadata_version_id: sourceMetadata.id,
      title,
      description,
      tags: tagsText
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
      hook_summary: hookSummary || null,
      youtube_account_id: youtubeAccountId || null,
    });
  }

  function ensureScheduleDefaults() {
    if (scheduleDate && scheduleTime) {
      return;
    }
    const nextSlot = getDefaultScheduleDateTime();
    setScheduleDate(formatDateInputValue(nextSlot));
    setScheduleTime(formatTimeInputValue(nextSlot));
  }

  function openScheduleForm() {
    ensureScheduleDefaults();
    setScheduleError(null);
    setIsScheduleFormOpen(true);
    window.setTimeout(() => {
      const input = dateInputRef.current as PickerInput | null;
      if (input?.showPicker) {
        input.showPicker();
      } else {
        input?.focus();
      }
    }, 0);
  }

  async function handleScheduleForSelectedTime() {
    setScheduleError(null);
    const scheduledAt = buildScheduledPublishAt(scheduleDate, scheduleTime);
    if (!scheduledAt) {
      setScheduleError("Choose both a publish date and publish time.");
      return;
    }
    if (scheduledAt.getTime() <= Date.now()) {
      setScheduleError("Choose a future publish date and time.");
      return;
    }
    await scheduleMutation.mutateAsync({
      youtube_account_id: youtubeAccountId || null,
      publish_mode: "scheduled",
      visibility: "public",
      scheduled_publish_at_utc: scheduledAt.toISOString(),
      use_next_available_slot: false,
    });
    setIsScheduleFormOpen(false);
  }

  async function handlePublishNow() {
    await scheduleMutation.mutateAsync({
      youtube_account_id: youtubeAccountId || null,
      publish_mode: "immediate",
      visibility,
    });
  }

  return (
    <PageFrame
      eyebrow="Publishing"
      title="Review Video Metadata"
      description="Review the generated YouTube draft, edit anything you want, assign the target channel, then approve and publish on your own timing."
      inspector={
        <div className="flex flex-col gap-4">
          <SectionCard title="Video Status">
            <div className="flex items-center gap-3">
              <StatusBadge status={video?.status ?? "uploaded"} />
              <span className="text-sm text-secondary">Updated {formatTimestamp(video?.updated_at)}</span>
            </div>
            <p className="mt-3 text-sm text-secondary">
              Approved metadata version: {video?.approved_metadata_version?.version_number ?? "None"}
            </p>
          </SectionCard>
          <SectionCard title="Publish Controls">
            <label className="text-[0.68rem] font-bold uppercase tracking-widest text-muted" htmlFor="target-account">
              Target YouTube Account
            </label>
            <select
              id="target-account"
              className="mt-2 rounded-xl border border-border-subtle bg-glass px-3 py-2 text-sm text-primary"
              value={youtubeAccountId}
              onChange={(event) => setYouTubeAccountId(event.target.value)}
            >
              <option value="">Choose an account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.channel_title}
                </option>
              ))}
            </select>
            <label className="mt-4 text-[0.68rem] font-bold uppercase tracking-widest text-muted" htmlFor="publish-visibility">
              Immediate Visibility
            </label>
            <select
              id="publish-visibility"
              className="mt-2 rounded-xl border border-border-subtle bg-glass px-3 py-2 text-sm text-primary"
              value={visibility}
              onChange={(event) => setVisibility(event.target.value as PublishVisibility)}
            >
              <option value="public">Public</option>
              <option value="unlisted">Unlisted</option>
              <option value="private">Private</option>
            </select>
            <div className="mt-4 flex flex-col gap-2">
              <button
                className={primaryActionButtonClassName}
                onClick={openScheduleForm}
                type="button"
                disabled={!canRunPublishAction}
              >
                Schedule Video
              </button>
              {isScheduleFormOpen ? (
                <div className="rounded-2xl border border-border-subtle bg-card/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Choose Publish Date</p>
                  <div className="mt-3 grid gap-3">
                    <label className="flex flex-col gap-2">
                      <span className="text-sm text-secondary">Date</span>
                      <input
                        ref={dateInputRef}
                        type="date"
                        className="rounded-xl border border-border-subtle bg-glass px-3 py-2 text-sm text-primary"
                        value={scheduleDate}
                        onChange={(event) => {
                          setScheduleDate(event.target.value);
                          setScheduleError(null);
                        }}
                        min={formatDateInputValue(new Date())}
                      />
                    </label>
                    <label className="flex flex-col gap-2">
                      <span className="text-sm text-secondary">Time</span>
                      <input
                        type="time"
                        className="rounded-xl border border-border-subtle bg-glass px-3 py-2 text-sm text-primary"
                        value={scheduleTime}
                        onChange={(event) => {
                          setScheduleTime(event.target.value);
                          setScheduleError(null);
                        }}
                        step={300}
                      />
                    </label>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-secondary">
                    The selected date and time use your browser's local timezone. Scheduled YouTube uploads publish
                    publicly at that moment.
                  </p>
                  {scheduleError ? <p className="mt-3 text-sm text-error">{scheduleError}</p> : null}
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      className={primaryActionButtonClassName}
                      onClick={() => void handleScheduleForSelectedTime()}
                      type="button"
                      disabled={!canRunPublishAction}
                    >
                      Schedule Now
                    </button>
                    <button
                      className={secondaryActionButtonClassName}
                      onClick={() => {
                        setIsScheduleFormOpen(false);
                        setScheduleError(null);
                      }}
                      type="button"
                      disabled={scheduleMutation.isPending}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : null}
              <button
                className={secondaryActionButtonClassName}
                onClick={() => void handlePublishNow()}
                type="button"
                disabled={!canRunPublishAction}
              >
                Publish Now
              </button>
              {publishActionMessage ? <p className="text-sm text-secondary">{publishActionMessage}</p> : null}
            </div>
          </SectionCard>
        </div>
      }
    >
      <PublishingLiveModeNotice />
      {error ? (
        <SectionCard title="Load Error">
          <p className="text-sm text-error">{error instanceof Error ? error.message : "Unable to load the video."}</p>
        </SectionCard>
      ) : null}
      {isLoading ? (
        <SectionCard title="Loading">
          <p className="text-sm text-secondary">Loading video metadata…</p>
        </SectionCard>
      ) : !video || !sourceMetadata ? (
        <SectionCard title="Metadata Pending">
          <PublishingEmptyState
            title="Metadata is not ready yet"
            description="Wait for transcription and metadata generation to complete, then refresh this page."
          />
        </SectionCard>
      ) : (
        <>
          <SectionCard
            title="Metadata Draft"
            subtitle="The generated title options, description, and tags come from the transcript. Your approved edit becomes the version used for scheduling and upload."
          >
            <div className="grid gap-5">
              <div>
                <p className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Generated Title Options</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {sourceMetadata.title_options.map((option) => (
                    <button
                      key={option}
                      className="rounded-full border border-border-subtle px-3 py-1.5 text-left text-xs text-secondary transition hover:border-border-active hover:text-primary"
                      onClick={() => setTitle(option)}
                      type="button"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>

              <label className="flex flex-col gap-2">
                <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Final Title</span>
                <input
                  className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Description</span>
                <textarea
                  className="min-h-40 rounded-2xl border border-border-subtle bg-glass px-4 py-3 text-sm leading-6 text-primary"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Tags</span>
                <input
                  className="rounded-xl border border-border-subtle bg-glass px-4 py-3 text-sm text-primary"
                  value={tagsText}
                  onChange={(event) => setTagsText(event.target.value)}
                  placeholder="shorts, growth, viral"
                />
              </label>

              <label className="flex flex-col gap-2">
                <span className="text-[0.68rem] font-bold uppercase tracking-widest text-muted">Hook / Summary</span>
                <textarea
                  className="min-h-28 rounded-2xl border border-border-subtle bg-glass px-4 py-3 text-sm leading-6 text-primary"
                  value={hookSummary}
                  onChange={(event) => setHookSummary(event.target.value)}
                />
              </label>

              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-full border border-border-active bg-primary-bg px-4 py-2 text-sm font-semibold text-primary"
                  onClick={() => void handleApprove()}
                  type="button"
                  disabled={approveMutation.isPending}
                >
                  {approveMutation.isPending ? "Saving…" : "Approve Metadata"}
                </button>
                {approveMutation.error ? (
                  <p className="self-center text-sm text-error">
                    {approveMutation.error instanceof Error ? approveMutation.error.message : "Approval failed."}
                  </p>
                ) : null}
                {scheduleMutation.error ? (
                  <p className="self-center text-sm text-error">
                    {scheduleMutation.error instanceof Error ? scheduleMutation.error.message : "Publish action failed."}
                  </p>
                ) : null}
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Transcript" subtitle="The local Whisper small model transcript is the source material for the generated metadata.">
            <p className="whitespace-pre-wrap text-sm leading-7 text-secondary">
              {video.transcript?.transcript_text ?? "Transcript is still being prepared."}
            </p>
          </SectionCard>
        </>
      )}
    </PageFrame>
  );
}

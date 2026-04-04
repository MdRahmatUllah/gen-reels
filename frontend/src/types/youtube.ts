export type PublishingVideoStatus =
  | "uploaded"
  | "transcribing"
  | "metadata_ready"
  | "scheduled"
  | "publishing"
  | "published"
  | "failed";

export type PublishMode = "immediate" | "scheduled";
export type PublishVisibility = "public" | "private" | "unlisted";
export type PublishJobStatus = "scheduled" | "queued" | "publishing" | "published" | "failed" | "cancelled";

export interface YouTubeAccount {
  id: string;
  google_account_email: string | null;
  channel_id: string;
  channel_title: string;
  channel_handle: string | null;
  is_default: boolean;
  token_expiry_at: string | null;
  connected_at: string;
  created_at: string;
  updated_at: string;
}

export interface PublishSchedule {
  id: string;
  youtube_account_id: string;
  timezone_name: string;
  slots_local: string[];
  is_active: boolean;
  next_available_slots_utc: string[];
  created_at: string;
  updated_at: string;
}

export interface PublishSchedulePayload {
  youtube_account_id: string;
  timezone_name: string;
  slots_local: string[];
  is_active: boolean;
}

export interface VideoTranscript {
  id: string;
  language_code: string;
  word_count: number;
  transcript_text: string;
  whisper_model_size: string;
  created_at: string;
  updated_at: string;
}

export interface VideoMetadataVersion {
  id: string;
  video_id: string;
  version_number: number;
  source_type: string;
  provider_name: string | null;
  provider_model: string | null;
  title_options: string[];
  recommended_title: string;
  title: string;
  description: string;
  tags: string[];
  hook_summary: string | null;
  is_approved: boolean;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PublishingVideo {
  id: string;
  youtube_account_id: string | null;
  approved_metadata_version_id: string | null;
  original_file_name: string;
  content_type: string;
  size_bytes: number;
  duration_ms: number | null;
  width: number | null;
  height: number | null;
  status: PublishingVideoStatus;
  scheduled_publish_at: string | null;
  published_at: string | null;
  youtube_video_id: string | null;
  processing_error_code: string | null;
  processing_error_message: string | null;
  created_at: string;
  updated_at: string;
  transcript: VideoTranscript | null;
  metadata_versions: VideoMetadataVersion[];
  approved_metadata_version: VideoMetadataVersion | null;
}

export interface ApproveVideoMetadataPayload {
  metadata_version_id?: string | null;
  title: string;
  description: string;
  tags: string[];
  hook_summary?: string | null;
  youtube_account_id?: string | null;
}

export interface ScheduleVideoPayload {
  youtube_account_id?: string | null;
  publish_mode: PublishMode;
  visibility: PublishVisibility;
  scheduled_publish_at_utc?: string | null;
  use_next_available_slot?: boolean;
}

export interface BatchSchedulePayload {
  youtube_account_id: string;
  video_ids: string[];
  preview_only: boolean;
}

export interface BatchScheduleAssignment {
  video_id: string;
  original_file_name: string;
  publish_at_utc: string;
  publish_at_local_label: string;
}

export interface BatchScheduleResult {
  preview_only: boolean;
  assignments: BatchScheduleAssignment[];
  created_job_ids: string[];
}

export interface PublishJob {
  id: string;
  video_id: string;
  youtube_account_id: string;
  metadata_version_id: string | null;
  publish_mode: PublishMode;
  visibility: PublishVisibility;
  scheduled_publish_at: string | null;
  status: PublishJobStatus;
  queued_at: string | null;
  started_at: string | null;
  published_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  youtube_video_id: string | null;
  youtube_video_url: string | null;
  attempt_count: number;
  error_code: string | null;
  error_message: string | null;
  last_progress_percent: number | null;
  created_at: string;
  updated_at: string;
  original_file_name: string | null;
  channel_title: string | null;
}

export interface VideoActionAcceptedResponse {
  video_id: string;
  status: string;
  message: string;
}

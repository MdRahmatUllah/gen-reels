import { api } from "./api-client";
import { isMockMode } from "./config";
import type {
  ApproveVideoMetadataPayload,
  BatchSchedulePayload,
  BatchScheduleResult,
  PublishJob,
  PublishSchedule,
  PublishSchedulePayload,
  PublishingVideo,
  ScheduleVideoPayload,
  VideoActionAcceptedResponse,
  YouTubeAccount,
} from "../types/youtube";

function requireLiveMode(): void {
  if (isMockMode()) {
    throw new Error("Publishing features require VITE_API_MODE=live.");
  }
}

export async function getYouTubeConnectUrl(redirectPath = "/app/publishing/accounts"): Promise<string> {
  requireLiveMode();
  const response = await api.get<{ authorization_url: string }>(
    `/integrations/youtube/connect?redirect_path=${encodeURIComponent(redirectPath)}`,
  );
  return response.authorization_url;
}

export async function listYouTubeAccounts(): Promise<YouTubeAccount[]> {
  requireLiveMode();
  return api.get<YouTubeAccount[]>("/integrations/youtube/accounts");
}

export async function disconnectYouTubeAccount(youtubeAccountId: string): Promise<void> {
  requireLiveMode();
  await api.post(`/integrations/youtube/disconnect/${youtubeAccountId}`);
}

export async function setDefaultYouTubeAccount(youtubeAccountId: string): Promise<YouTubeAccount> {
  requireLiveMode();
  return api.post<YouTubeAccount>(`/integrations/youtube/accounts/${youtubeAccountId}/default`);
}

export async function listPublishingVideos(): Promise<PublishingVideo[]> {
  requireLiveMode();
  return api.get<PublishingVideo[]>("/videos");
}

export async function getPublishingVideo(videoId: string): Promise<PublishingVideo> {
  requireLiveMode();
  return api.get<PublishingVideo>(`/videos/${videoId}`);
}

export async function uploadPublishingVideo(file: File): Promise<PublishingVideo> {
  requireLiveMode();
  const formData = new FormData();
  formData.append("file", file);
  return api.post<PublishingVideo>("/videos/upload", formData);
}

export async function generatePublishingMetadata(videoId: string): Promise<VideoActionAcceptedResponse> {
  requireLiveMode();
  return api.post<VideoActionAcceptedResponse>(`/videos/${videoId}/generate-metadata`);
}

export async function approvePublishingMetadata(
  videoId: string,
  payload: ApproveVideoMetadataPayload,
): Promise<PublishingVideo> {
  requireLiveMode();
  return api.post<PublishingVideo>(`/videos/${videoId}/approve-metadata`, payload);
}

export async function listPublishSchedules(): Promise<PublishSchedule[]> {
  requireLiveMode();
  return api.get<PublishSchedule[]>("/youtube/schedules");
}

export async function createPublishSchedule(payload: PublishSchedulePayload): Promise<PublishSchedule> {
  requireLiveMode();
  return api.post<PublishSchedule>("/youtube/schedules", payload);
}

export async function updatePublishSchedule(
  scheduleId: string,
  payload: PublishSchedulePayload,
): Promise<PublishSchedule> {
  requireLiveMode();
  return api.put<PublishSchedule>(`/youtube/schedules/${scheduleId}`, payload);
}

export async function schedulePublishingVideo(
  videoId: string,
  payload: ScheduleVideoPayload,
): Promise<PublishJob> {
  requireLiveMode();
  return api.post<PublishJob>(`/videos/${videoId}/schedule`, payload);
}

export async function batchSchedulePublishingVideos(payload: BatchSchedulePayload): Promise<BatchScheduleResult> {
  requireLiveMode();
  return api.post<BatchScheduleResult>("/videos/batch-schedule", payload);
}

export async function listPublishJobs(): Promise<PublishJob[]> {
  requireLiveMode();
  return api.get<PublishJob[]>("/publish-jobs");
}

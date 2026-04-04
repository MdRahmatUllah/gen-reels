import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  ApproveVideoMetadataPayload,
  BatchSchedulePayload,
  PublishSchedulePayload,
  ScheduleVideoPayload,
} from "../types/youtube";
import {
  approvePublishingMetadata,
  batchSchedulePublishingVideos,
  createPublishSchedule,
  disconnectYouTubeAccount,
  generatePublishingMetadata,
  getPublishingVideo,
  listPublishJobs,
  listPublishSchedules,
  listPublishingVideos,
  listYouTubeAccounts,
  schedulePublishingVideo,
  setDefaultYouTubeAccount,
  updatePublishSchedule,
  uploadPublishingVideo,
} from "../lib/youtube-api";

export function useYouTubeAccounts() {
  return useQuery({
    queryKey: ["youtube-accounts"],
    queryFn: listYouTubeAccounts,
    refetchInterval: 15_000,
  });
}

export function useDisconnectYouTubeAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (youtubeAccountId: string) => disconnectYouTubeAccount(youtubeAccountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["youtube-accounts"] });
      queryClient.invalidateQueries({ queryKey: ["publish-schedules"] });
      queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
      queryClient.invalidateQueries({ queryKey: ["publish-jobs"] });
    },
  });
}

export function useSetDefaultYouTubeAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (youtubeAccountId: string) => setDefaultYouTubeAccount(youtubeAccountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["youtube-accounts"] });
    },
  });
}

export function usePublishingVideos() {
  return useQuery({
    queryKey: ["publishing-videos"],
    queryFn: listPublishingVideos,
    refetchInterval: 10_000,
  });
}

export function usePublishingVideo(videoId: string) {
  return useQuery({
    queryKey: ["publishing-video", videoId],
    queryFn: () => getPublishingVideo(videoId),
    enabled: Boolean(videoId),
    refetchInterval: 10_000,
  });
}

export function useUploadPublishingVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadPublishingVideo(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
      queryClient.invalidateQueries({ queryKey: ["publish-jobs"] });
    },
  });
}

export function useGeneratePublishingMetadata() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (videoId: string) => generatePublishingMetadata(videoId),
    onSuccess: (_, videoId) => {
      queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
      queryClient.invalidateQueries({ queryKey: ["publishing-video", videoId] });
    },
  });
}

export function useApprovePublishingMetadata(videoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApproveVideoMetadataPayload) => approvePublishingMetadata(videoId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
      queryClient.invalidateQueries({ queryKey: ["publishing-video", videoId] });
      queryClient.invalidateQueries({ queryKey: ["publish-jobs"] });
    },
  });
}

export function usePublishSchedules() {
  return useQuery({
    queryKey: ["publish-schedules"],
    queryFn: listPublishSchedules,
    refetchInterval: 30_000,
  });
}

export function useCreatePublishSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PublishSchedulePayload) => createPublishSchedule(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publish-schedules"] });
      queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
    },
  });
}

export function useUpdatePublishSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ scheduleId, payload }: { scheduleId: string; payload: PublishSchedulePayload }) =>
      updatePublishSchedule(scheduleId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publish-schedules"] });
    },
  });
}

export function useSchedulePublishingVideo(videoId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScheduleVideoPayload) => schedulePublishingVideo(videoId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
      queryClient.invalidateQueries({ queryKey: ["publishing-video", videoId] });
      queryClient.invalidateQueries({ queryKey: ["publish-jobs"] });
    },
  });
}

export function useBatchSchedulePublishingVideos() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BatchSchedulePayload) => batchSchedulePublishingVideos(payload),
    onSuccess: (result) => {
      if (!result.preview_only) {
        queryClient.invalidateQueries({ queryKey: ["publishing-videos"] });
        queryClient.invalidateQueries({ queryKey: ["publish-jobs"] });
      }
    },
  });
}

export function usePublishJobs() {
  return useQuery({
    queryKey: ["publish-jobs"],
    queryFn: listPublishJobs,
    refetchInterval: 10_000,
  });
}

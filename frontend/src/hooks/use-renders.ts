import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetRenders,
  mockStartRender,
  mockCancelRender,
  mockRetryRenderStep,
} from "../lib/mock-service";
import {
  liveGetRenders,
  liveStartRender,
  liveCancelRender,
  liveRetryRenderStep,
  liveApproveFramePair,
  liveRegenerateFramePair,
  liveGenerateNarration,
} from "../lib/live-api";
import type { NarrationResult } from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useRenders(projectId: string) {
  return useQuery({
    queryKey: ["renders", projectId],
    queryFn: () => (isMockMode() ? mockGetRenders(projectId) : liveGetRenders(projectId)),
    enabled: !!projectId,
    // Poll every 2 seconds to simulate SSE updates when the UI is mounted
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data?.length) return false;
      const active = data.some((r) =>
        ["running", "queued", "review"].includes(r.status),
      );
      if (active) return 1500;
      // Newest job first from API; poll lightly so a retry moves failed → queued without manual refresh.
      const latest = data.reduce((a, b) =>
        new Date(b.createdAt).getTime() > new Date(a.createdAt).getTime() ? b : a,
      );
      if (latest.status === "failed") return 4000;
      return false;
    },
  });
}

export function useStartRender(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (settings?: { subtitleStyle: string; musicDucking: string; musicTrack: string; }) =>
      isMockMode() ? mockStartRender(projectId, settings) : liveStartRender(projectId, settings),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useCancelRender(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => (isMockMode() ? mockCancelRender(projectId) : liveCancelRender(projectId)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
    },
  });
}

export function useRetryRenderStep(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) =>
      isMockMode() ? mockRetryRenderStep(projectId, stepId) : liveRetryRenderStep(projectId, stepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
    },
  });
}

export function useApproveFramePair(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (stepId: string) => {
      if (isMockMode()) return;
      await liveApproveFramePair(projectId, stepId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useRegenerateFramePair(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (stepId: string) => {
      if (isMockMode()) return;
      await liveRegenerateFramePair(projectId, stepId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useGenerateNarration(projectId: string) {
  const qc = useQueryClient();
  return useMutation<
    NarrationResult,
    Error,
    { renderJobId: string; sceneSegmentId: string; voice?: string }
  >({
    mutationFn: ({ renderJobId, sceneSegmentId, voice }) =>
      liveGenerateNarration(renderJobId, sceneSegmentId, voice),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
    },
  });
}

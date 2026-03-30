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
} from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useRenders(projectId: string) {
  return useQuery({
    queryKey: ["renders", projectId],
    queryFn: () => (isMockMode() ? mockGetRenders(projectId) : liveGetRenders(projectId)),
    enabled: !!projectId,
    // Poll every 2 seconds to simulate SSE updates when the UI is mounted
    refetchInterval: (query) => {
      const data = query.state.data;
      if (
        data &&
        data.length > 0 &&
        (data[0].status === "running" || data[0].status === "queued" || data[0].status === "review")
      ) {
        return 1500; // Fast 1.5s refresh for fluid UI
      }
      return false; // Stop polling on error, complete, or empty
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
    },
  });
}

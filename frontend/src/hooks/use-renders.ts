import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetRenders,
  mockStartRender,
  mockCancelRender,
  mockRetryRenderStep,
} from "../lib/mock-service";

export function useRenders(projectId: string) {
  return useQuery({
    queryKey: ["renders", projectId],
    queryFn: () => mockGetRenders(projectId),
    enabled: !!projectId,
    // Poll every 2 seconds to simulate SSE updates when the UI is mounted
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.length > 0 && data[0].status === "running") {
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
      mockStartRender(projectId, settings),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useCancelRender(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => mockCancelRender(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
    },
  });
}

export function useRetryRenderStep(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) => mockRetryRenderStep(projectId, stepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["renders", projectId] });
    },
  });
}

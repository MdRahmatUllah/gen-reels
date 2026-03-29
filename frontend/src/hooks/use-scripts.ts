import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetScript,
  mockGenerateScript,
  mockUpdateScript,
  mockApproveScript,
} from "../lib/mock-service";
import {
  liveGetScript,
  liveGenerateScript,
  liveUpdateScript,
  liveApproveScript,
} from "../lib/live-api";
import { isMockMode } from "../lib/config";
import type { ScriptData } from "../types/domain";

export function useScript(projectId: string) {
  return useQuery({
    queryKey: ["script", projectId],
    queryFn: () => (isMockMode() ? mockGetScript(projectId) : liveGetScript(projectId)),
    enabled: !!projectId,
    refetchInterval: isMockMode() ? false : 2000,
  });
}

export function useGenerateScript(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      isMockMode() ? mockGenerateScript(projectId) : liveGenerateScript(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["script", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

export function useUpdateScript(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (updates: Partial<ScriptData>) =>
      isMockMode() ? mockUpdateScript(projectId, updates) : liveUpdateScript(projectId, updates),
    onSuccess: (updated) => {
      queryClient.setQueryData(["script", projectId], updated);
    },
  });
}

export function useApproveScript(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      isMockMode() ? mockApproveScript(projectId) : liveApproveScript(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["script", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

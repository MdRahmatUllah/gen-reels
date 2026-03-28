import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetScript,
  mockGenerateScript,
  mockUpdateScript,
  mockApproveScript,
} from "../lib/mock-service";
import type { ScriptData } from "../types/domain";

export function useScript(projectId: string) {
  return useQuery({
    queryKey: ["script", projectId],
    queryFn: () => mockGetScript(projectId),
    enabled: !!projectId,
  });
}

export function useGenerateScript(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => mockGenerateScript(projectId),
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
    mutationFn: (updates: Partial<ScriptData>) => mockUpdateScript(projectId, updates),
    onSuccess: (updated) => {
      queryClient.setQueryData(["script", projectId], updated);
    },
  });
}

export function useApproveScript(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => mockApproveScript(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["script", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

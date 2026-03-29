import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ScenePlan } from "../types/domain";
import {
  mockGetScenePlan,
  mockGenerateScenePlan,
  mockGeneratePromptPairs,
  mockUpdateScene,
  mockApproveScenePlan,
  mockSetScenePlanPreset,
} from "../lib/mock-service";

export function useScenePlan(projectId: string) {
  return useQuery({
    queryKey: ["scenePlan", projectId],
    queryFn: () => mockGetScenePlan(projectId),
    enabled: !!projectId,
  });
}

export function useGenerateScenePlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => mockGenerateScenePlan(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useGeneratePromptPairs(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sceneId: string) => mockGeneratePromptPairs(projectId, sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
    },
  });
}

export function useUpdateScene(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sceneId, updates }: { sceneId: string; updates: Partial<ScenePlan> }) =>
      mockUpdateScene(projectId, sceneId, updates),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
    },
  });
}

export function useApproveScenePlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => mockApproveScenePlan(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useSetScenePlanPreset(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, presetId }: { type: "visual" | "voice"; presetId: string }) =>
      mockSetScenePlanPreset(projectId, type, presetId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
    },
  });
}

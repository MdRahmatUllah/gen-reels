import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ScenePlan } from "../types/domain";
import { useQuickCreateStatus } from "./use-projects";
import {
  mockGetScenePlan,
  mockGenerateScenePlan,
  mockGeneratePromptPairs,
  mockUpdateScene,
  mockApproveScenePlan,
  mockSetScenePlanPreset,
} from "../lib/mock-service";
import {
  liveGetScenePlan,
  liveGenerateScenePlan,
  liveGeneratePromptPairs,
  liveUpdateScene,
  liveApproveScenePlan,
  liveSetScenePlanPreset,
} from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useScenePlan(projectId: string) {
  const { data: quickCreate } = useQuickCreateStatus(projectId);

  return useQuery({
    queryKey: ["scenePlan", projectId],
    queryFn: () => (isMockMode() ? mockGetScenePlan(projectId) : liveGetScenePlan(projectId)),
    enabled: !!projectId,
    refetchInterval: (query) => {
      if (isMockMode()) {
        return false;
      }
      const plan = query.state.data;
      if (plan?.status === "running" || plan?.status === "queued") {
        return 2500;
      }
      if (quickCreate?.isActive) {
        return 4000;
      }
      return false;
    },
  });
}

export function useGenerateScenePlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      isMockMode() ? mockGenerateScenePlan(projectId) : liveGenerateScenePlan(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });
}

export function useGeneratePromptPairs(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sceneId: string) =>
      isMockMode()
        ? mockGeneratePromptPairs(projectId, sceneId)
        : liveGeneratePromptPairs(projectId, sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
    },
  });
}

export function useUpdateScene(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sceneId, updates }: { sceneId: string; updates: Partial<ScenePlan> }) =>
      isMockMode()
        ? mockUpdateScene(projectId, sceneId, updates)
        : liveUpdateScene(projectId, sceneId, updates),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
    },
  });
}

export function useApproveScenePlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      isMockMode() ? mockApproveScenePlan(projectId) : liveApproveScenePlan(projectId),
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
      isMockMode()
        ? mockSetScenePlanPreset(projectId, type, presetId)
        : liveSetScenePlanPreset(projectId, type, presetId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenePlan", projectId] });
    },
  });
}

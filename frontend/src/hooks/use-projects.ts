import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetProjects,
  mockGetProject,
  mockCreateProject,
  mockQuickCreateProject,
  mockGetQuickCreateStatus,
} from "../lib/mock-service";
import {
  liveGetProjects,
  liveGetProject,
  liveCreateProject,
  liveQuickCreateProject,
  liveGetQuickCreateStatus,
} from "../lib/live-api";
import type {
  CreateProjectPayload,
  QuickCreateProjectPayload,
} from "../types/domain";
import { isMockMode } from "../lib/config";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: isMockMode() ? mockGetProjects : liveGetProjects,
    refetchInterval: isMockMode() ? false : 5000,
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => (isMockMode() ? mockGetProject(projectId) : liveGetProject(projectId)),
    enabled: !!projectId,
    refetchInterval: isMockMode() ? false : 5000,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateProjectPayload) =>
      isMockMode() ? mockCreateProject(payload) : liveCreateProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

export function useQuickCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: QuickCreateProjectPayload) =>
      isMockMode() ? mockQuickCreateProject(payload) : liveQuickCreateProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

export function useQuickCreateStatus(projectId: string) {
  return useQuery({
    queryKey: ["quick-create-status", projectId],
    queryFn: () =>
      isMockMode() ? mockGetQuickCreateStatus(projectId) : liveGetQuickCreateStatus(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      const status = query.state.data as { isActive?: boolean } | undefined;
      return status?.isActive ? 1500 : false;
    },
  });
}

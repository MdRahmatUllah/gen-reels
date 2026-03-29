import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetProjects,
  mockGetProject,
  mockCreateProject,
} from "../lib/mock-service";
import {
  liveGetProjects,
  liveGetProject,
  liveCreateProject,
} from "../lib/live-api";
import type { CreateProjectPayload } from "../types/domain";
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

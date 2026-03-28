import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetProjects,
  mockGetProject,
  mockCreateProject,
} from "../lib/mock-service";
import type { CreateProjectPayload } from "../types/domain";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: mockGetProjects,
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => mockGetProject(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateProjectPayload) => mockCreateProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

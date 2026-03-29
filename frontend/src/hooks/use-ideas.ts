import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetIdeas,
  mockGenerateIdeas,
  mockSelectIdea,
} from "../lib/mock-service";
import {
  liveGetIdeas,
  liveGenerateIdeas,
  liveSelectIdea,
} from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useIdeas(projectId: string) {
  return useQuery({
    queryKey: ["ideas", projectId],
    queryFn: () => (isMockMode() ? mockGetIdeas(projectId) : liveGetIdeas(projectId)),
    enabled: !!projectId,
    refetchInterval: isMockMode() ? false : 2000,
  });
}

export function useGenerateIdeas(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => (isMockMode() ? mockGenerateIdeas(projectId) : liveGenerateIdeas(projectId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ideas", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

export function useSelectIdea(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ideaId: string) =>
      isMockMode() ? mockSelectIdea(projectId, ideaId) : liveSelectIdea(projectId, ideaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

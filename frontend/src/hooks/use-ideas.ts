import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetIdeas,
  mockGenerateIdeas,
  mockSelectIdea,
} from "../lib/mock-service";

export function useIdeas(projectId: string) {
  return useQuery({
    queryKey: ["ideas", projectId],
    queryFn: () => mockGetIdeas(projectId),
    enabled: !!projectId,
  });
}

export function useGenerateIdeas(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => mockGenerateIdeas(projectId),
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
    mutationFn: (ideaId: string) => mockSelectIdea(projectId, ideaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

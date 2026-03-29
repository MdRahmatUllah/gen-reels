import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetBrief, mockUpdateBrief } from "../lib/mock-service";
import { liveGetBrief, liveUpdateBrief } from "../lib/live-api";
import { isMockMode } from "../lib/config";
import type { BriefData } from "../types/domain";

export function useBrief(projectId: string) {
  return useQuery({
    queryKey: ["brief", projectId],
    queryFn: () => (isMockMode() ? mockGetBrief(projectId) : liveGetBrief(projectId)),
    enabled: !!projectId,
  });
}

export function useUpdateBrief(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<BriefData>) =>
      isMockMode() ? mockUpdateBrief(projectId, data) : liveUpdateBrief(projectId, data),
    onSuccess: (updatedBrief) => {
      queryClient.setQueryData(["brief", projectId], updatedBrief);
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["shell-data"] });
    },
  });
}

import { useQuery } from "@tanstack/react-query";
import { mockGetExports } from "../lib/mock-service";
import { liveGetExports } from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useExports(projectId: string) {
  return useQuery({
    queryKey: ["exports", projectId],
    queryFn: () => (isMockMode() ? mockGetExports(projectId) : liveGetExports(projectId)),
    enabled: !!projectId,
  });
}

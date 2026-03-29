import { useQuery } from "@tanstack/react-query";
import { mockGetExports } from "../lib/mock-service";

export function useExports(projectId: string) {
  return useQuery({
    queryKey: ["exports", projectId],
    queryFn: () => mockGetExports(projectId),
    enabled: !!projectId,
  });
}

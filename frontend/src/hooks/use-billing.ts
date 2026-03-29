import { useQuery } from "@tanstack/react-query";
import { mockGetBilling } from "../lib/mock-service";
import { liveGetBilling } from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useBilling() {
  return useQuery({
    queryKey: ["billing"],
    queryFn: isMockMode() ? mockGetBilling : liveGetBilling,
    // Poll every 3 seconds to show live credit depletion dynamically
    refetchInterval: 3000,
  });
}

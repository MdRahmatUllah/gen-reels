import { useQuery } from "@tanstack/react-query";
import { mockGetBilling } from "../lib/mock-service";

export function useBilling() {
  return useQuery({
    queryKey: ["billing"],
    queryFn: mockGetBilling,
    // Poll every 3 seconds to show live credit depletion dynamically
    refetchInterval: 3000,
  });
}

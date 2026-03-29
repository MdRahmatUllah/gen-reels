import { useQuery } from "@tanstack/react-query";
import { mockGetAssets } from "../lib/mock-service";

export function useAssets() {
  return useQuery({
    queryKey: ["assets"],
    queryFn: mockGetAssets,
  });
}

import { useQuery } from "@tanstack/react-query";
import { mockGetAssets } from "../lib/mock-service";
import { liveGetAssets } from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useAssets() {
  return useQuery({
    queryKey: ["assets"],
    queryFn: isMockMode() ? mockGetAssets : liveGetAssets,
  });
}

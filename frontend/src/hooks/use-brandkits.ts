import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetBrandKits, mockSaveBrandKit } from "../lib/mock-service";
import { liveGetBrandKits, liveSaveBrandKit } from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useBrandKits() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["brandKits"],
    queryFn: isMockMode() ? mockGetBrandKits : liveGetBrandKits,
  });

  const saveKit = useMutation({
    mutationFn: isMockMode() ? mockSaveBrandKit : liveSaveBrandKit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brandKits"] });
    },
  });

  return {
    ...query,
    saveKit: saveKit.mutateAsync,
    isSaving: saveKit.isPending,
  };
}

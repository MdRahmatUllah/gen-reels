import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetBrandKits, mockSaveBrandKit } from "../lib/mock-service";
import type { BrandKit } from "../types/domain";

export function useBrandKits() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["brandKits"],
    queryFn: mockGetBrandKits,
  });

  const saveKit = useMutation({
    mutationFn: mockSaveBrandKit,
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

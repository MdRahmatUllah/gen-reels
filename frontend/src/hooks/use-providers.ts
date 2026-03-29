import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetProviderKeys,
  mockAddProviderKey,
  mockDeleteProviderKey,
  mockGetLocalWorkers,
} from "../lib/mock-service";
import type { ProviderKey } from "../types/domain";

export function useProviderKeys() {
  return useQuery({
    queryKey: ["providerKeys"],
    queryFn: mockGetProviderKeys,
  });
}

export function useAddProviderKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ provider, key }: { provider: ProviderKey["provider"]; key: string }) =>
      mockAddProviderKey(provider, key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providerKeys"] });
    },
  });
}

export function useDeleteProviderKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: mockDeleteProviderKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providerKeys"] });
    },
  });
}

export function useLocalWorkers() {
  return useQuery({
    queryKey: ["localWorkers"],
    queryFn: mockGetLocalWorkers,
  });
}

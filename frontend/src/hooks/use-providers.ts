import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  mockCreateProviderCredential,
  mockDeleteProviderCredential,
  mockGetExecutionPolicy,
  mockGetLocalWorkers,
  mockGetProviderCredentials,
  mockUpdateExecutionPolicyRoute,
  mockUpdateProviderCredential,
  mockValidateProviderCredential,
} from "../lib/mock-service";
import {
  liveCreateProviderCredential,
  liveDeleteProviderCredential,
  liveGetExecutionPolicy,
  liveGetLocalWorkers,
  liveGetProviderCredentials,
  liveUpdateExecutionPolicyRoute,
  liveUpdateProviderCredential,
  liveValidateProviderCredential,
} from "../lib/live-api";
import { isMockMode } from "../lib/config";
import type {
  ProviderCredentialInput,
  ProviderCredentialRecord,
  ProviderModality,
} from "../types/domain";

export function useProviderCredentials() {
  return useQuery({
    queryKey: ["providerCredentials"],
    queryFn: isMockMode() ? mockGetProviderCredentials : liveGetProviderCredentials,
  });
}

export function useProviderExecutionPolicy() {
  return useQuery({
    queryKey: ["providerExecutionPolicy"],
    queryFn: isMockMode() ? mockGetExecutionPolicy : liveGetExecutionPolicy,
  });
}

function invalidateProviderQueries(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["providerCredentials"] });
  queryClient.invalidateQueries({ queryKey: ["providerExecutionPolicy"] });
  queryClient.invalidateQueries({ queryKey: ["settings"] });
}

export function useCreateProviderCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ProviderCredentialInput) =>
      isMockMode() ? mockCreateProviderCredential(input) : liveCreateProviderCredential(input),
    onSuccess: () => invalidateProviderQueries(queryClient),
  });
}

export function useUpdateProviderCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      credentialId,
      input,
    }: {
      credentialId: string;
      input: ProviderCredentialInput;
    }) =>
      isMockMode()
        ? mockUpdateProviderCredential(credentialId, input)
        : liveUpdateProviderCredential(credentialId, input),
    onSuccess: () => invalidateProviderQueries(queryClient),
  });
}

export function useDeleteProviderCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: isMockMode() ? mockDeleteProviderCredential : liveDeleteProviderCredential,
    onSuccess: () => invalidateProviderQueries(queryClient),
  });
}

export function useValidateProviderCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: isMockMode() ? mockValidateProviderCredential : liveValidateProviderCredential,
    onSuccess: () => invalidateProviderQueries(queryClient),
  });
}

export function useUpdateProviderRoute() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      modality,
      providerKey,
      credentialId,
      mode,
    }: {
      modality: ProviderModality;
      providerKey: string;
      credentialId: string | null;
      mode: "hosted" | "byo" | "local";
    }) =>
      isMockMode()
        ? mockUpdateExecutionPolicyRoute(modality, providerKey, credentialId, mode)
        : liveUpdateExecutionPolicyRoute(modality, providerKey, credentialId, mode),
    onSuccess: () => invalidateProviderQueries(queryClient),
  });
}

export function useLocalWorkers() {
  return useQuery({
    queryKey: ["localWorkers"],
    queryFn: isMockMode() ? mockGetLocalWorkers : liveGetLocalWorkers,
  });
}

export function findCredentialById(
  credentials: ProviderCredentialRecord[] | undefined,
  credentialId: string | null,
): ProviderCredentialRecord | undefined {
  if (!credentials || !credentialId) {
    return undefined;
  }
  return credentials.find((credential) => credential.id === credentialId);
}

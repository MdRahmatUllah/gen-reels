import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  mockGetAdminQueue,
  mockGetAdminWorkspaces,
  mockGetAdminRenders,
  mockApproveQueueItem,
  mockRejectQueueItem,
} from "../lib/mock-service";
import {
  liveGetAdminQueue,
  liveGetAdminWorkspaces,
  liveGetAdminRenders,
  liveApproveQueueItem,
  liveRejectQueueItem,
} from "../lib/live-api";
import { isMockMode } from "../lib/config";

export function useAdminQueue() {
  return useQuery({
    queryKey: ["admin", "queue"],
    queryFn: isMockMode() ? mockGetAdminQueue : liveGetAdminQueue,
    refetchInterval: 3000,
  });
}

export function useAdminWorkspaces() {
  return useQuery({
    queryKey: ["admin", "workspaces"],
    queryFn: isMockMode() ? mockGetAdminWorkspaces : liveGetAdminWorkspaces,
    refetchInterval: 10000,
  });
}

export function useAdminRenders() {
  return useQuery({
    queryKey: ["admin", "renders"],
    queryFn: isMockMode() ? mockGetAdminRenders : liveGetAdminRenders,
    refetchInterval: 3000,
  });
}

export function useReleaseQueueItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      isMockMode() ? mockApproveQueueItem(jobId) : liveApproveQueueItem(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["renders"] });
    },
  });
}

export function useRejectQueueItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      isMockMode() ? mockRejectQueueItem(jobId) : liveRejectQueueItem(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["renders"] });
    },
  });
}

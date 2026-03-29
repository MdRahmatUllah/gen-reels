import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  mockGetAdminQueue, 
  mockGetAdminWorkspaces, 
  mockGetAdminRenders,
  mockApproveQueueItem,
  mockRejectQueueItem
} from "../lib/mock-service";

export function useAdminQueue() {
  return useQuery({
    queryKey: ["admin", "queue"],
    queryFn: mockGetAdminQueue,
    refetchInterval: 3000, 
  });
}

export function useAdminWorkspaces() {
  return useQuery({
    queryKey: ["admin", "workspaces"],
    queryFn: mockGetAdminWorkspaces,
    refetchInterval: 10000,
  });
}

export function useAdminRenders() {
  return useQuery({
    queryKey: ["admin", "renders"],
    queryFn: mockGetAdminRenders,
    refetchInterval: 3000,
  });
}

export function useReleaseQueueItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => mockApproveQueueItem(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["renders"] });
    }
  });
}

export function useRejectQueueItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => mockRejectQueueItem(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["renders"] });
    }
  });
}

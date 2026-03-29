import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetComments, mockAddComment, mockResolveComment } from "../lib/mock-service";

export function useComments(targetId: string) {
  return useQuery({
    queryKey: ["comments", targetId],
    queryFn: () => mockGetComments(targetId),
  });
}

export function useAddComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ targetId, text }: { targetId: string; text: string }) => mockAddComment(targetId, text),
    onSuccess: (_, { targetId }) => {
      queryClient.invalidateQueries({ queryKey: ["comments", targetId] });
    },
  });
}

export function useResolveComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) => mockResolveComment(commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comments"] });
    },
  });
}

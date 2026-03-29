import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetComments, mockAddComment, mockResolveComment } from "../lib/mock-service";
import { liveGetComments, liveAddComment, liveResolveComment } from "../lib/live-api";
import { isMockMode } from "../lib/config";

type CommentTargetOptions = {
  projectId?: string;
  targetType?: string;
};

export function useComments(targetId: string, options: CommentTargetOptions = {}) {
  return useQuery({
    queryKey: ["comments", targetId, options.projectId ?? "", options.targetType ?? "scene_segment"],
    queryFn: () =>
      isMockMode() ? mockGetComments(targetId, options) : liveGetComments(targetId, options),
  });
}

export function useAddComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      targetId,
      text,
      options,
    }: {
      targetId: string;
      text: string;
      options?: CommentTargetOptions;
    }) => (isMockMode() ? mockAddComment(targetId, text, options) : liveAddComment(targetId, text, options)),
    onSuccess: (_, { targetId, options }) => {
      queryClient.invalidateQueries({
        queryKey: ["comments", targetId, options?.projectId ?? "", options?.targetType ?? "scene_segment"],
      });
    },
  });
}

export function useResolveComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) =>
      isMockMode() ? mockResolveComment(commentId) : liveResolveComment(commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comments"] });
    },
  });
}

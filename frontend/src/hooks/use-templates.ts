import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetTemplates, mockCloneTemplate } from "../lib/mock-service";
import { liveGetTemplates, liveCloneTemplate } from "../lib/live-api";
import { isMockMode } from "../lib/config";
import { useNavigate } from "react-router-dom";

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: isMockMode() ? mockGetTemplates : liveGetTemplates,
  });
}

export function useCloneTemplate() {
  const qc = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (templateId: string) =>
      isMockMode() ? mockCloneTemplate(templateId) : liveCloneTemplate(templateId),
    onSuccess: (newProjectId) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      // Reroute the user immediately to the newly cloned project's brief
      navigate(`/app/projects/${newProjectId}/brief`);
    },
  });
}

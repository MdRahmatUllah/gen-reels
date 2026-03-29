import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mockGetTemplates, mockCloneTemplate } from "../lib/mock-service";
import { useNavigate } from "react-router-dom";

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: mockGetTemplates,
  });
}

export function useCloneTemplate() {
  const qc = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (templateId: string) => mockCloneTemplate(templateId),
    onSuccess: (newProjectId) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      // Reroute the user immediately to the newly cloned project's brief
      navigate(`/app/projects/${newProjectId}/brief`);
    },
  });
}

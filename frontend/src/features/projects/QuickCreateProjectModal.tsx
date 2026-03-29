import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Dialog } from "../../components/Dialog";
import { useQuickCreateProject } from "../../hooks/use-projects";
import { useTemplates } from "../../hooks/use-templates";

export function QuickCreateProjectModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { data: templates, isLoading } = useTemplates();
  const quickCreateProject = useQuickCreateProject();
  const [ideaPrompt, setIdeaPrompt] = useState("");
  const [starterValue, setStarterValue] = useState("studio_default");

  useEffect(() => {
    if (!open) {
      setIdeaPrompt("");
      setStarterValue("studio_default");
    }
  }, [open]);

  const selectedTemplate = useMemo(() => {
    if (!starterValue.startsWith("template:")) {
      return null;
    }
    const templateId = starterValue.replace("template:", "");
    return templates?.find((template) => template.id === templateId) ?? null;
  }, [starterValue, templates]);

  const canSubmit = ideaPrompt.trim().length > 0 && starterValue.length > 0;

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!quickCreateProject.isPending) {
          onClose();
        }
      }}
      title="Create New Project"
      actions={
        <>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"
            onClick={onClose}
            disabled={quickCreateProject.isPending}
          >
            Cancel
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            disabled={!canSubmit || quickCreateProject.isPending}
            onClick={() => {
              const starterMode = starterValue === "studio_default" ? "studio_default" : "template";
              const templateId = starterMode === "template" ? starterValue.replace("template:", "") : null;
              quickCreateProject.mutate(
                {
                  ideaPrompt: ideaPrompt.trim(),
                  starterMode,
                  templateId,
                },
                {
                  onSuccess: (result) => {
                    onClose();
                    navigate(result.redirectPath);
                  },
                },
              );
            }}
          >
            {quickCreateProject.isPending ? "Starting..." : "Create and auto-generate"}
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="form-field">
          <label
            className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1"
            htmlFor="quick-create-idea"
          >
            Idea or title
          </label>
          <textarea
            id="quick-create-idea"
            className="field-input field-textarea"
            rows={5}
            value={ideaPrompt}
            onChange={(event) => setIdeaPrompt(event.target.value)}
            placeholder="Describe the reel idea, offer, audience, hook, or just paste a working title."
          />
          <p className="text-[0.82rem] text-secondary mt-2">
            The platform will generate the project title, brief, ideas, script, prompt pairs, and approved scene plan from this input.
          </p>
        </div>

        <div className="form-field">
          <label
            className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1"
            htmlFor="quick-create-starter"
          >
            Starter preset
          </label>
          <select
            id="quick-create-starter"
            className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"
            value={starterValue}
            onChange={(event) => setStarterValue(event.target.value)}
          >
            <option value="studio_default">Studio Default</option>
            {(templates ?? []).map((template) => (
              <option key={template.id} value={`template:${template.id}`}>
                {template.name}
              </option>
            ))}
          </select>
          <p className="text-[0.82rem] text-secondary mt-2">
            {starterValue === "studio_default"
              ? "Balanced platform defaults work even in a brand-new workspace."
              : selectedTemplate
                ? `${selectedTemplate.description} Recommended duration ${selectedTemplate.duration}.`
                : isLoading
                  ? "Loading reusable starters..."
                  : "Template-backed starters apply project defaults without copying the old brief verbatim."}
          </p>
        </div>

        {quickCreateProject.error instanceof Error ? (
          <div className="rounded-xl border border-error-bg bg-error-bg px-4 py-3 text-sm text-error">
            {quickCreateProject.error.message}
          </div>
        ) : null}
      </div>
    </Dialog>
  );
}

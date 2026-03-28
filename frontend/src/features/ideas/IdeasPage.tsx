import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useIdeas, useGenerateIdeas, useSelectIdea } from "../../hooks/use-ideas";
import { useProject } from "../../hooks/use-projects";
import { mockGetBrief } from "../../lib/mock-service";
import { GenerationStatusIndicator } from "../../components/GenerationStatus";
import { PageFrame, SectionCard, MetricCard, StatusBadge } from "../../components/ui";
import type { IdeaCandidate } from "../../types/domain";

export function IdeasPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project } = useProject(projectId!);
  const { data: ideaSet } = useIdeas(projectId!);
  const generateIdeas = useGenerateIdeas(projectId!);
  const selectIdea = useSelectIdea(projectId!);
  const { data: brief } = useQuery({
    queryKey: ["brief", projectId],
    queryFn: () => mockGetBrief(projectId!),
    enabled: !!projectId,
  });

  const [selectedId, setSelectedId] = useState<string | null>(project?.selectedIdeaId ?? null);

  if (!project || !projectId) return null;

  const ideas = ideaSet?.ideas ?? [];
  const isGenerating = generateIdeas.isPending || ideaSet?.status === "running";
  const hasIdeas = ideas.length > 0;
  const canContinue = selectedId !== null;

  const handleGenerate = () => {
    generateIdeas.mutate();
  };

  const handleSelect = (idea: IdeaCandidate) => {
    setSelectedId(idea.id);
    selectIdea.mutate(idea.id);
  };

  const handleContinue = () => {
    navigate(`/app/projects/${projectId}/script`);
  };

  return (
    <PageFrame
      eyebrow="Idea workspace"
      title={`${project.title} — Viral Ideas`}
      description="Generate and evaluate viral content ideas before committing to a script. Select one idea as the creative anchor."
      actions={
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            className="button button--secondary"
            onClick={handleGenerate}
            disabled={isGenerating}
            type="button"
          >
            {isGenerating ? "Generating…" : hasIdeas ? "Regenerate ideas" : "Generate ideas"}
          </button>
          {canContinue ? (
            <button
              className="button button--primary"
              onClick={handleContinue}
              type="button"
            >
              Continue to script →
            </button>
          ) : null}
        </div>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Brief context">
            <div className="inspector-list">
              <div>
                <span>Objective</span>
                <strong>{brief?.objective || "Not set"}</strong>
              </div>
              <div>
                <span>Hook</span>
                <strong>{brief?.hook || "Not set"}</strong>
              </div>
              <div>
                <span>Audience</span>
                <strong>{brief?.targetAudience || "Not set"}</strong>
              </div>
            </div>
          </SectionCard>

          {selectedId ? (
            <SectionCard title="Selected idea">
              <div className="inspector-list">
                <div>
                  <span>Status</span>
                  <StatusBadge status="approved" />
                </div>
                <div>
                  <span>Idea</span>
                  <strong>{ideas.find((i) => i.id === selectedId)?.title ?? "—"}</strong>
                </div>
              </div>
            </SectionCard>
          ) : null}
        </div>
      }
    >
      {/* Generation state */}
      {isGenerating ? (
        <SectionCard className="surface-card--hero" title="Generating viral ideas…" subtitle="The AI is crafting content concepts based on your brief">
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", padding: "2rem 0" }}>
            <GenerationStatusIndicator status="running" label="Analyzing brief and generating ideas…" />
            <div className="shimmer" style={{ height: "6rem", borderRadius: "0.5rem" }} />
            <div className="shimmer" style={{ height: "6rem", borderRadius: "0.5rem" }} />
            <div className="shimmer" style={{ height: "6rem", borderRadius: "0.5rem" }} />
          </div>
        </SectionCard>
      ) : null}

      {/* Empty state */}
      {!isGenerating && !hasIdeas ? (
        <SectionCard
          className="surface-card--hero"
          title="No ideas generated yet"
          subtitle="Click 'Generate ideas' to create viral content concepts from your brief"
        >
          <div style={{ textAlign: "center", padding: "3rem 0" }}>
            <p className="body-copy" style={{ maxWidth: "32rem", margin: "0 auto 1.5rem" }}>
              The AI will analyze your brief's objective, target audience, and brand guidelines to generate 5-6 viral content ideas ranked by potential engagement.
            </p>
            <button className="button button--primary" onClick={handleGenerate} type="button">
              Generate ideas
            </button>
          </div>
        </SectionCard>
      ) : null}

      {/* Idea cards */}
      {!isGenerating && hasIdeas ? (
        <>
          <SectionCard
            title="Generated ideas"
            subtitle={`${ideas.length} concepts ranked by viral potential — select one to continue`}
          >
            <div className="artifact-grid">
              {ideas
                .sort((a, b) => b.viralScore - a.viralScore)
                .map((idea) => {
                  const isSelected = selectedId === idea.id;
                  return (
                    <div
                      key={idea.id}
                      className={`surface-card ${isSelected ? "surface-card--hero" : ""}`}
                      style={{
                        cursor: "pointer",
                        transition: "all 0.2s ease",
                        outline: isSelected ? "2px solid var(--color-primary, #004ced)" : "none",
                        outlineOffset: "-2px",
                      }}
                      onClick={() => handleSelect(idea)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleSelect(idea);
                        }
                      }}
                      aria-pressed={isSelected}
                    >
                      <div className="section-header">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", width: "100%" }}>
                          <div>
                            <h3>{idea.title}</h3>
                            <p style={{ opacity: 0.7 }}>{idea.angle}</p>
                          </div>
                          {isSelected ? (
                            <StatusBadge status="approved" />
                          ) : null}
                        </div>
                      </div>
                      <p className="body-copy" style={{ fontStyle: "italic", margin: "0.75rem 0" }}>
                        "{idea.hook}"
                      </p>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div className="tag-row">
                          {idea.tags.map((tag) => (
                            <span className="tag-chip" key={tag}>
                              {tag}
                            </span>
                          ))}
                        </div>
                        <MetricCard
                          label="Viral score"
                          value={`${idea.viralScore}`}
                          detail="out of 100"
                          tone={idea.viralScore >= 90 ? "success" : idea.viralScore >= 85 ? "primary" : "neutral"}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          </SectionCard>
        </>
      ) : null}
    </PageFrame>
  );
}

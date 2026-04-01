import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useIdeas, useGenerateIdeas, useSelectIdea } from "../../hooks/use-ideas";
import { useProject } from "../../hooks/use-projects";
import { mockGetBrief } from "../../lib/mock-service";
import { GenerationStatusIndicator } from "../../components/GenerationStatus";
import { PageFrame, SectionCard, StatusBadge } from "../../components/ui";
import type { IdeaCandidate } from "../../types/domain";

/* ─── Score Ring ──────────────────────────────────────────────────────────── */
function ScoreRing({ score, size = 56 }: { score: number; size?: number }) {
  const stroke = 4.5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 90
      ? "var(--success-fg)"
      : score >= 80
        ? "var(--accent)"
        : score >= 70
          ? "var(--warning-fg)"
          : "var(--neutral-fg)";

  return (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border-subtle)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <span className="absolute text-[0.9rem] font-bold text-primary font-heading">{score}</span>
    </div>
  );
}

/* ─── Rank Badge ──────────────────────────────────────────────────────────── */
function RankBadge({ rank }: { rank: number }) {
  const styles: Record<number, string> = {
    1: "bg-[rgba(245,158,11,0.15)] text-[#f59e0b] border-[rgba(245,158,11,0.25)] shadow-[0_0_8px_rgba(245,158,11,0.12)]",
    2: "bg-[rgba(148,163,184,0.15)] text-[#94a3b8] border-[rgba(148,163,184,0.2)]",
    3: "bg-[rgba(234,88,12,0.12)] text-[#ea580c] border-[rgba(234,88,12,0.2)]",
  };

  const base = "inline-flex items-center justify-center h-7 min-w-[1.75rem] px-2 rounded-lg text-xs font-bold font-heading border";
  const style = styles[rank] ?? "bg-glass text-muted border-border-subtle";

  return <span className={`${base} ${style}`}>#{rank}</span>;
}

/* ─── Icons ───────────────────────────────────────────────────────────────── */
function SparklesIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
    </svg>
  );
}

function ArrowRightIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function CheckIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function LightbulbIcon({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  );
}

/* ─── Idea Card ───────────────────────────────────────────────────────────── */
function IdeaCard({
  idea,
  rank,
  isSelected,
  onSelect,
  delay,
}: {
  idea: IdeaCandidate;
  rank: number;
  isSelected: boolean;
  onSelect: () => void;
  delay: number;
}) {
  const scoreColor =
    idea.viralScore >= 90
      ? "var(--success-fg)"
      : idea.viralScore >= 80
        ? "var(--accent)"
        : idea.viralScore >= 70
          ? "var(--warning-fg)"
          : "var(--neutral-fg)";

  return (
    <div
      className={`idea-card group ${isSelected ? "idea-card--selected" : ""}`}
      style={{ animationDelay: `${delay}ms` }}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      aria-pressed={isSelected}
    >
      {/* Top: rank + selected badge + score ring */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <RankBadge rank={rank} />
          {isSelected && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-success-bg text-success text-[0.7rem] font-bold border border-success-glow">
              <CheckIcon />
              Selected
            </span>
          )}
        </div>
        <ScoreRing score={idea.viralScore} />
      </div>

      {/* Title + angle */}
      <div className="flex flex-col gap-1 mt-1">
        <h3 className="font-heading text-[1.1rem] font-bold text-primary leading-snug group-hover:text-accent transition-colors duration-200">
          {idea.title}
        </h3>
        <p className="text-[0.85rem] text-secondary leading-relaxed">{idea.angle}</p>
      </div>

      {/* Hook as a pull-quote */}
      <p className="idea-quote">&ldquo;{idea.hook}&rdquo;</p>

      {/* Tags */}
      <div className="flex flex-wrap items-center gap-1.5 mt-3">
        {idea.tags.map((tag) => (
          <span className="tag-chip" key={tag}>
            {tag}
          </span>
        ))}
      </div>

      {/* Score bar */}
      <div className="flex items-center gap-3 mt-4 pt-3.5 border-t border-border-subtle">
        <div className="flex-1">
          <div className="h-1.5 w-full bg-border-subtle rounded-full overflow-hidden">
            <div
              className="idea-score-bar"
              style={{
                width: `${idea.viralScore}%`,
                background: idea.viralScore >= 80 ? "var(--accent-gradient)" : scoreColor,
                boxShadow: idea.viralScore >= 80 ? "0 0 8px var(--accent-glow)" : "none",
              }}
            />
          </div>
        </div>
        <span className="text-[0.7rem] font-bold text-muted whitespace-nowrap tracking-wide uppercase">
          {idea.viralScore}/100
        </span>
      </div>
    </div>
  );
}

/* ─── Empty State ─────────────────────────────────────────────────────────── */
function EmptyIdeasState({ onGenerate }: { onGenerate: () => void }) {
  const features = [
    { label: "Objective analysis", detail: "Your brief's goal drives the creative direction" },
    { label: "Audience targeting", detail: "Ideas optimized for your target viewers" },
    { label: "Viral scoring", detail: "Each concept ranked by engagement potential" },
  ];

  return (
    <div className="idea-empty">
      <div className="idea-empty__icon">
        <LightbulbIcon />
      </div>
      <div className="flex flex-col gap-2 max-w-md">
        <h3 className="font-heading text-xl font-bold text-primary">Ready to brainstorm</h3>
        <p className="text-[0.9rem] leading-relaxed text-secondary">
          Generate AI-powered content ideas tailored to your brief. Each idea comes with a viral score, hook, and creative angle.
        </p>
      </div>
      <div className="flex flex-col gap-2 text-left max-w-sm w-full">
        {features.map((item) => (
          <div key={item.label} className="idea-empty__feature">
            <span className="idea-empty__dot" />
            <div className="flex flex-col">
              <strong className="text-sm font-semibold text-primary">{item.label}</strong>
              <span className="text-xs text-secondary">{item.detail}</span>
            </div>
          </div>
        ))}
      </div>
      <button className="btn-primary mt-2" onClick={onGenerate} type="button">
        <SparklesIcon size={15} />
        Generate ideas
      </button>
    </div>
  );
}

/* ─── Generating Skeleton ─────────────────────────────────────────────────── */
function GeneratingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-start gap-4 rounded-xl border border-border-subtle bg-glass p-4">
          <div className="shimmer h-14 w-14 rounded-xl shrink-0" />
          <div className="flex-1 flex flex-col gap-2.5">
            <div className="shimmer h-4 w-2/3 rounded-full" />
            <div className="shimmer h-3 w-full rounded-full" />
            <div className="shimmer h-3 w-4/5 rounded-full" />
            <div className="flex gap-2 mt-1">
              <div className="shimmer h-5 w-16 rounded-full" />
              <div className="shimmer h-5 w-20 rounded-full" />
              <div className="shimmer h-5 w-14 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── Inspector: Selection Prompt ─────────────────────────────────────────── */
function SelectionPrompt() {
  return (
    <SectionCard title="Selection">
      <div className="flex flex-col items-center gap-2.5 py-3 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-glass text-muted">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
            <path d="M22 4L12 14.01l-3-3" />
          </svg>
        </div>
        <p className="text-xs text-secondary leading-relaxed max-w-[14rem]">
          Click an idea card to select it as your creative anchor
        </p>
      </div>
    </SectionCard>
  );
}

/* ─── Inspector: Selected Idea Detail ─────────────────────────────────────── */
function SelectedIdeaInspector({ idea }: { idea: IdeaCandidate }) {
  return (
    <SectionCard title="Selected idea">
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <StatusBadge status="approved" />
          <ScoreRing score={idea.viralScore} size={44} />
        </div>
        <div className="flex flex-col gap-1">
          <strong className="text-sm font-semibold text-primary">{idea.title}</strong>
          <p className="text-xs text-secondary leading-relaxed">{idea.angle}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {idea.tags.map((tag) => (
            <span className="tag-chip" key={tag}>{tag}</span>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}

/* ─── Inspector: Overview Stats ───────────────────────────────────────────── */
function OverviewInspector({ ideas }: { ideas: IdeaCandidate[] }) {
  const sorted = [...ideas].sort((a, b) => b.viralScore - a.viralScore);
  const avg = Math.round(ideas.reduce((sum, i) => sum + i.viralScore, 0) / ideas.length);

  return (
    <SectionCard title="Overview">
      <div className="inspector-list">
        <div>
          <span>Total ideas</span>
          <strong>{ideas.length}</strong>
        </div>
        <div>
          <span>Top score</span>
          <strong>{sorted[0]?.viralScore ?? "—"}/100</strong>
        </div>
        <div>
          <span>Avg score</span>
          <strong>{avg}/100</strong>
        </div>
      </div>
    </SectionCard>
  );
}

/* ─── Ideas Page ──────────────────────────────────────────────────────────── */
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
  const [queuedGeneration, setQueuedGeneration] = useState(false);

  useEffect(() => {
    setSelectedId(project?.selectedIdeaId ?? null);
  }, [project?.selectedIdeaId]);

  useEffect(() => {
    if ((ideaSet?.ideas.length ?? 0) > 0) {
      setQueuedGeneration(false);
    }
  }, [ideaSet?.ideas.length]);

  if (!project || !projectId) return null;

  const ideas = ideaSet?.ideas ?? [];
  const isGenerating = queuedGeneration || generateIdeas.isPending || ideaSet?.status === "running";
  const hasIdeas = ideas.length > 0;
  const canContinue = selectedId !== null;
  const sortedIdeas = [...ideas].sort((a, b) => b.viralScore - a.viralScore);
  const selectedIdea = ideas.find((i) => i.id === selectedId);

  const handleGenerate = () => {
    setQueuedGeneration(true);
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
        <div className="flex items-center gap-3">
          {hasIdeas && !isGenerating ? (
            <button className="btn-ghost" onClick={handleGenerate} disabled={isGenerating} type="button">
              <SparklesIcon size={15} />
              Regenerate
            </button>
          ) : null}
          {!hasIdeas && !isGenerating ? (
            <button className="btn-primary" onClick={handleGenerate} disabled={isGenerating} type="button">
              <SparklesIcon size={15} />
              Generate ideas
            </button>
          ) : null}
          {canContinue ? (
            <button className="btn-primary" onClick={handleContinue} type="button">
              Continue to script
              <ArrowRightIcon size={15} />
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
                <span>Hook angle</span>
                <strong>{brief?.hook || "Not set"}</strong>
              </div>
              <div>
                <span>Audience</span>
                <strong>{brief?.targetAudience || "Not set"}</strong>
              </div>
            </div>
          </SectionCard>

          {selectedIdea ? (
            <SelectedIdeaInspector idea={selectedIdea} />
          ) : hasIdeas ? (
            <SelectionPrompt />
          ) : null}

          {hasIdeas ? <OverviewInspector ideas={ideas} /> : null}
        </div>
      }
    >
      {/* Generating state */}
      {isGenerating ? (
        <SectionCard
          className="surface-card--hero"
          title="Generating viral ideas..."
          subtitle="The AI is crafting content concepts based on your brief"
        >
          <div className="flex flex-col gap-5 py-2">
            <GenerationStatusIndicator status="running" label="Analyzing brief and generating ideas..." />
            <GeneratingSkeleton />
          </div>
        </SectionCard>
      ) : null}

      {/* Empty state */}
      {!isGenerating && !hasIdeas ? <EmptyIdeasState onGenerate={handleGenerate} /> : null}

      {/* Idea cards */}
      {!isGenerating && hasIdeas ? (
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-0.5">
              <h3 className="font-heading text-[1.05rem] font-bold text-primary">Generated ideas</h3>
              <p className="text-[0.85rem] text-secondary">
                {ideas.length} concepts ranked by viral potential{!canContinue ? " — select one to continue" : ""}
              </p>
            </div>
            <span className="text-[0.7rem] font-bold text-muted px-3 py-1.5 rounded-full bg-glass border border-border-subtle uppercase tracking-wider whitespace-nowrap">
              {canContinue ? "1" : "0"} / {ideas.length} selected
            </span>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {sortedIdeas.map((idea, index) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                rank={index + 1}
                isSelected={selectedId === idea.id}
                onSelect={() => handleSelect(idea)}
                delay={index * 60}
              />
            ))}
          </div>
        </div>
      ) : null}
    </PageFrame>
  );
}

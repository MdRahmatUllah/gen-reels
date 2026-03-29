import { LoadingPage, MetricCard, PageFrame, SectionCard } from "../../components/ui";
import { useCloneTemplate, useTemplates } from "../../hooks/use-templates";

export function TemplatesPage() {
  const { data, isLoading } = useTemplates();
  const { mutate: cloneTemplate, isPending: isCloning } = useCloneTemplate();

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Templates"
      title="Production starters"
      description="Select a robust template to skip mundane setup and start with a perfect visual foundation."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Template intent">
            <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
              Each template packages a scene count, duration band, and visual tone, preloading the
              Brief stage so you can jump straight to Idea Generation.
            </p>
          </SectionCard>
        </div>
      }
    >
      <div className="artifact-grid">
        {data.map((template) => (
          <SectionCard key={template.id} title={template.name} subtitle={template.description}>
            <div className="metric-row">
              <MetricCard label="Duration band" value={template.duration} detail="Recommended length" tone="primary" />
              <MetricCard label="Scenes" value={String(template.scenes)} detail={template.style} tone="neutral" />
            </div>
            <div className="border-t border-border-subtle pt-4">
              <button
                className="inline-flex w-full items-center justify-center rounded-xl bg-accent-gradient px-4 py-3 text-sm font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent disabled:opacity-60"
                onClick={() => cloneTemplate(template.id)}
                disabled={isCloning}
                type="button"
              >
                {isCloning ? "Copying template..." : "Use Template"}
              </button>
            </div>
          </SectionCard>
        ))}
      </div>
    </PageFrame>
  );
}

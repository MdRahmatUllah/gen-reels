import { PageFrame, SectionCard, MetricCard, LoadingPage } from "../../components/ui";
import { useTemplates, useCloneTemplate } from "../../hooks/use-templates";

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
            <p className="body-copy">
              Each template packages a scene count, duration band, and visual tone, preloading the Brief stage so you can jump straight to Idea Generation.
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
            <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--color-border-subtle)" }}>
              <button
                className="button button--primary"
                style={{ width: "100%" }}
                onClick={() => cloneTemplate(template.id)}
                disabled={isCloning}
              >
                {isCloning ? "Copying template..." : "Use Template →"}
              </button>
            </div>
          </SectionCard>
        ))}
      </div>
    </PageFrame>
  );
}

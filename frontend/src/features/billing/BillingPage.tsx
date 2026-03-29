import { PageFrame, SectionCard, ProgressBar, StatusBadge, LoadingPage } from "../../components/ui";
import { useBilling } from "../../hooks/use-billing";

export function BillingPage() {
  const { data, isLoading } = useBilling();

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Billing"
      title="Metered production economics"
      description="Generation is a metered product. Watch credits deplete in real-time as render jobs execute."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Plan status">
            <div className="inspector-list">
              <div>
                <span>Plan</span>
                <strong>{data.planName}</strong>
              </div>
              <div>
                <span>Cycle</span>
                <strong>{data.cycleLabel}</strong>
              </div>
              <div>
                <span>Projected spend</span>
                <strong>{data.projectedSpend}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard className="surface-card--hero" title="Credit position" subtitle={data.cycleLabel}>
        <ProgressBar
          value={(data.creditsRemaining / data.creditsTotal) * 100}
          label="Credits remaining"
          detail={`${data.creditsRemaining} of ${data.creditsTotal} credits left`}
        />
      </SectionCard>

      <SectionCard title="Usage breakdown" subtitle="Recorded automatically by the render orchestration engine">
        <div className="table-shell">
          <table className="studio-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Usage</th>
                <th>Unit cost</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {data.usageBreakdown.map((row) => (
                <tr key={row.category}>
                  <td>{row.category}</td>
                  <td>{row.usage}</td>
                  <td>{row.unitCost}</td>
                  <td>{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard title="Invoices and reviews" subtitle="Subscription and overage visibility">
        <div className="project-list">
          {data.invoices.map((invoice) => (
            <div className="project-list__item" key={invoice.id}>
              <div>
                <p className="eyebrow">{invoice.date}</p>
                <strong>{invoice.label}</strong>
                <p>{invoice.amount}</p>
              </div>
              <StatusBadge status={invoice.status as any} />
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}

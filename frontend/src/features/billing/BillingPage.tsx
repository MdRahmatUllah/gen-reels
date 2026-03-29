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
        <div className="flex flex-col gap-4">
          <SectionCard title="Plan status">
            <div className="flex flex-col gap-3 p-1">
              <div className="flex justify-between items-center text-sm border-b border-slate-800/50 pb-2">
                <span className="text-slate-400">Plan</span>
                <strong className="text-slate-200 font-semibold">{data.planName}</strong>
              </div>
              <div className="flex justify-between items-center text-sm border-b border-slate-800/50 pb-2">
                <span className="text-slate-400">Cycle</span>
                <strong className="text-slate-200 font-semibold">{data.cycleLabel}</strong>
              </div>
              <div className="flex justify-between items-center text-sm pb-1">
                <span className="text-slate-400">Projected spend</span>
                <strong className="text-slate-200 font-semibold">{data.projectedSpend}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      <SectionCard className="border-accent-cyan/50 shadow-[0_0_20px_rgba(34,211,238,0.05)]" title="Credit position" subtitle={data.cycleLabel}>
        <ProgressBar
          value={(data.creditsRemaining / data.creditsTotal) * 100}
          label="Credits remaining"
          detail={`${data.creditsRemaining} of ${data.creditsTotal} credits left`}
        />
      </SectionCard>

      <SectionCard title="Usage breakdown" subtitle="Recorded automatically by the render orchestration engine">
        <div className="overflow-x-auto rounded-lg border border-slate-800/60 bg-slate-900/40">
          <table className="w-full text-left text-sm text-slate-300">
            <thead>
              <tr>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Category</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Usage</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Unit cost</th>
                <th className="border-b border-slate-800/60 bg-slate-900/80 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.usageBreakdown.map((row) => (
                <tr key={row.category} className="hover:bg-slate-800/30 transition-colors">
                  <td className="border-b border-slate-800/50 px-4 py-3 font-medium text-slate-200">{row.category}</td>
                  <td className="border-b border-slate-800/50 px-4 py-3">{row.usage}</td>
                  <td className="border-b border-slate-800/50 px-4 py-3">{row.unitCost}</td>
                  <td className="border-b border-slate-800/50 px-4 py-3 font-mono text-xs">{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard title="Invoices and reviews" subtitle="Subscription and overage visibility">
        <div className="flex flex-col gap-2">
          {data.invoices.map((invoice) => (
            <div className="flex items-center justify-between p-4 rounded-lg bg-slate-900/50 border border-slate-800/50 hover:border-slate-700/50 transition-colors" key={invoice.id}>
              <div className="flex flex-col gap-0.5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-0.5">{invoice.date}</p>
                <strong className="text-sm font-semibold text-slate-200 block">{invoice.label}</strong>
                <p className="text-xs text-slate-400 mt-0.5">{invoice.amount}</p>
              </div>
              <StatusBadge status={invoice.status as any} />
            </div>
          ))}
        </div>
      </SectionCard>
    </PageFrame>
  );
}

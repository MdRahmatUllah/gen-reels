import { useState, useMemo } from "react";
import { PageFrame, SectionCard, StatusBadge, EmptyState, LoadingPage } from "../../components/ui";
import { useAssets } from "../../hooks/use-assets";

export function AssetsPage() {
  const { data, isLoading } = useAssets();
  const [filterType, setFilterType] = useState<"all" | "image" | "video" | "audio">("all");

  const filteredAssets = useMemo(() => {
    if (!data) return [];
    if (filterType === "all") return data;
    return data.filter(asset => asset.type === filterType);
  }, [data, filterType]);

  if (isLoading || !data) {
    return <LoadingPage />;
  }

  return (
    <PageFrame
      eyebrow="Asset library"
      title="Global asset lineage"
      description="Easily browse, trace, and reuse prior generated assets across all your workspaces to accelerate creation."
      actions={
        <div className="filter-row">
          {(["all", "image", "video", "audio"] as const).map((type) => (
            <button
              key={type}
              className={filterType === type ? "chip-button chip-button--active" : "chip-button"}
              onClick={() => setFilterType(type)}
              type="button"
            >
              {type === "all" ? "All types" : type}
            </button>
          ))}
        </div>
      }
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Asset usage">
            <div className="inspector-list">
              <div>
                <span>Total items</span>
                <strong>{data.length}</strong>
              </div>
              <div>
                <span>Approved videos</span>
                <strong>{data.filter(a => a.type === "video" && a.tags.includes("approved")).length}</strong>
              </div>
              <div>
                <span>Reusable tracks</span>
                <strong>{data.filter(a => a.type === "audio").length}</strong>
              </div>
            </div>
          </SectionCard>
        </div>
      }
    >
      {filteredAssets.length === 0 ? (
        <EmptyState title="No assets found" description={`No matching assets for filter: ${filterType}`} />
      ) : (
        <div className="artifact-grid">
          {filteredAssets.map((asset) => (
            <div key={asset.id} className="surface-card p-0" style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}>
              <div style={{ height: "160px", width: "100%", background: `url(${asset.thumbnailUrl})` }} />
              <div style={{ padding: "16px", flex: "1" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                   <StatusBadge status={asset.type as any} />
                   <span style={{ fontSize: "11px", color: "var(--color-ink-lighter)" }}>
                     {new Date(asset.createdAt).toLocaleDateString()}
                   </span>
                </div>
                <strong style={{ display: "block", marginBottom: "8px", fontSize: "14px" }}>
                  {asset.prompt.length > 50 ? asset.prompt.substring(0, 50) + "..." : asset.prompt}
                </strong>
                <div className="tag-row" style={{ marginTop: "auto" }}>
                  {asset.tags.map((tag) => (
                    <span className="tag-chip" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ padding: "12px 16px", borderTop: "1px solid var(--color-border)", background: "var(--color-surface)" }}>
                 <p style={{ margin: 0, fontSize: "12px", color: "var(--color-ink-lighter)" }}>
                   {asset.sourceProjectId ? `From: ${asset.sourceProjectId}` : "Generated independently"}
                 </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageFrame>
  );
}

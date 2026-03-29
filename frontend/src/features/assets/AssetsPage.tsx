import { useMemo, useState } from "react";

import { EmptyState, LoadingPage, PageFrame, SectionCard, StatusBadge } from "../../components/ui";
import { useAssets } from "../../hooks/use-assets";

export function AssetsPage() {
  const { data, isLoading } = useAssets();
  const [filterType, setFilterType] = useState<"all" | "image" | "video" | "audio">("all");

  const filteredAssets = useMemo(() => {
    if (!data) {
      return [];
    }
    if (filterType === "all") {
      return data;
    }
    return data.filter((asset) => asset.type === filterType);
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
        <div className="flex flex-wrap items-center gap-2">
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
                <strong>{data.filter((asset) => asset.type === "video" && asset.tags.includes("approved")).length}</strong>
              </div>
              <div>
                <span>Reusable tracks</span>
                <strong>{data.filter((asset) => asset.type === "audio").length}</strong>
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
            <div key={asset.id} className="surface-card overflow-hidden p-0">
              <div
                className="h-40 w-full bg-cover bg-center"
                style={{ backgroundImage: `url(${asset.thumbnailUrl})` }}
              />
              <div className="flex flex-1 flex-col p-4">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <StatusBadge status={asset.type} />
                  <span className="text-[11px] text-muted">
                    {new Date(asset.createdAt).toLocaleDateString()}
                  </span>
                </div>

                <strong className="mb-3 block text-sm font-semibold text-primary">
                  {asset.prompt.length > 50 ? `${asset.prompt.substring(0, 50)}...` : asset.prompt}
                </strong>

                <div className="mt-auto flex flex-wrap items-center gap-2">
                  {asset.tags.map((tag) => (
                    <span className="tag-chip" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="border-t border-border-subtle bg-card-raised px-4 py-3">
                <p className="text-xs text-muted">
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

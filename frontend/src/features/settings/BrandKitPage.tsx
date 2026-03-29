import { useEffect, useState } from "react";

import { FormInput } from "../../components/FormField";
import { LoadingPage, PageFrame, SectionCard } from "../../components/ui";
import { useBrandKits } from "../../hooks/use-brandkits";
import type { BrandKit } from "../../types/domain";

export function BrandKitPage() {
  const { data: brandKits, isLoading, saveKit, isSaving } = useBrandKits();
  const [activeKit, setActiveKit] = useState<Partial<BrandKit>>({});

  useEffect(() => {
    if (brandKits && brandKits.length > 0) {
      setActiveKit(brandKits[0]);
    }
  }, [brandKits]);

  if (isLoading || !brandKits) {
    return <LoadingPage />;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!activeKit.name || !activeKit.primaryPalette) {
      return;
    }

    try {
      await saveKit(activeKit as BrandKit);
      alert("Brand Kit saved successfully!");
    } catch {
      alert("Failed to save brand kit");
    }
  };

  return (
    <PageFrame
      eyebrow="Workspace Settings"
      title="Brand Kits"
      description="Define the core visual identity for this workspace. When templates are cloned or new scenes generated, the orchestrator will pull from these brand settings to enforce structural consistency."
      inspector={
        <div className="inspector-stack">
          <SectionCard title="Why use a Brand Kit?">
            <p className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]">
              Brand kits ensure your prompts are automatically enriched with your specific lighting,
              tone, and hexadecimal colors. Keep your creators aligned without micromanaging.
            </p>
          </SectionCard>
        </div>
      }
    >
      <div className="surface-card limit-width">
        <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
          <FormInput
            id="name"
            label="Brand Name"
            value={activeKit.name || ""}
            onChange={(value) => setActiveKit({ ...activeKit, name: value })}
          />

          <FormInput
            id="northStar"
            label="Brand North Star"
            help="A short phrase defining your brand's mood. This gets appended to generation prompts."
            value={activeKit.brandNorthStar || ""}
            onChange={(value) => setActiveKit({ ...activeKit, brandNorthStar: value })}
          />

          <FormInput
            id="palette"
            label="Primary Palette"
            value={activeKit.primaryPalette || ""}
            onChange={(value) => setActiveKit({ ...activeKit, primaryPalette: value })}
            placeholder="e.g. Cobalt blue and ivory (#003366, #fffff0)"
          />

          <FormInput
            id="fontFamily"
            label="Font Family"
            value={activeKit.fontFamily || ""}
            onChange={(value) => setActiveKit({ ...activeKit, fontFamily: value })}
            placeholder="e.g. Inter, Manrope"
          />

          <div className="flex justify-end">
            <button
              type="submit"
              className="inline-flex items-center justify-center rounded-xl bg-accent-gradient px-4 py-3 text-sm font-semibold text-on-accent shadow-sm transition-all duration-200 hover:-translate-y-px hover:shadow-accent disabled:opacity-60"
              disabled={isSaving}
            >
              {isSaving ? "Saving..." : "Save Brand Kit"}
            </button>
          </div>
        </form>
      </div>
    </PageFrame>
  );
}

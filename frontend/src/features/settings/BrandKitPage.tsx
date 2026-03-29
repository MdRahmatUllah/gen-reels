import React, { useState, useEffect } from "react";
import { PageFrame, LoadingPage } from "../../components/ui";
import { FormInput } from "../../components/FormField";
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

  if (isLoading || !brandKits) return <LoadingPage />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeKit.name || !activeKit.primaryPalette) return;
    try {
      await saveKit(activeKit as BrandKit);
      alert("Brand Kit saved successfully!");
    } catch (err) {
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
          <div className="surface-card">
            <h3 className="section-heading">Why use a Brand Kit?</h3>
            <p className="body-copy" style={{ color: "var(--color-ink-lighter)" }}>
              Brand kits ensure your prompts are automatically enriched with your specific lighting, tone, and hexadecimal colors. Keep your creators aligned without micromanaging.
            </p>
          </div>
        </div>
      }
    >
      <div className="surface-card limit-width">
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <FormInput
            id="name"
            label="Brand Name"
            value={activeKit.name || ""}
            onChange={(val) => setActiveKit({ ...activeKit, name: val })}
          />

          <FormInput
            id="northStar"
            label="Brand North Star"
            help="A short phrase defining your brand's mood (e.g., 'Luxurious, dark, ASMR'). Appended to AI generation prompts."
            value={activeKit.brandNorthStar || ""}
            onChange={(val) => setActiveKit({ ...activeKit, brandNorthStar: val })}
          />

          <FormInput
            id="palette"
            label="Primary Palette"
            value={activeKit.primaryPalette || ""}
            onChange={(val) => setActiveKit({ ...activeKit, primaryPalette: val })}
            placeholder="e.g. Cobalt blue and ivory (#003366, #fffff0)"
          />

          <FormInput
            id="fontFamily"
            label="Font Family"
            value={activeKit.fontFamily || ""}
            onChange={(val) => setActiveKit({ ...activeKit, fontFamily: val })}
            placeholder="e.g. Inter, Roboto, Arial"
          />

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="button button--primary" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save Brand Kit"}
            </button>
          </div>
        </form>
      </div>
    </PageFrame>
  );
}

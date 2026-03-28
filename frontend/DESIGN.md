# Design System Strategy: The Production Atelier

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Director’s Desk."** 

Unlike generic SaaS platforms that feel like "software," this system must feel like a high-end production studio—think of a physical edit suite with matte surfaces, precision instruments, and a focused atmosphere. We are moving away from the "playful app" aesthetic toward a **"Clean Production Studio"** vibe. It is calm, structured, and operational. 

To break the "template" look, we utilize **Intentional Asymmetry**. We favor a heavy-left navigation and a wide, expansive canvas that allows media to breathe. We reject the "boxed-in" feeling of traditional grids in favor of **Layered Depth** and **Tonal Transitions**. The goal is an editorial experience where the UI recedes, and the creator’s content takes center stage.

---

## 2. Colors & Surface Logic
The palette is rooted in a sophisticated range of neutrals, using blue as a surgical strike of focus.

### The "No-Line" Rule
**Borders are forbidden for structural sectioning.** Do not use `1px` solid lines to separate the navigation from the canvas or the canvas from the inspector. Instead, define boundaries through background shifts:
- **Navigation Rail:** `surface-container-low` (#f1f3ff)
- **Main Canvas:** `surface` (#f9f9ff)
- **Inspector Panel:** `surface-container-lowest` (#ffffff)

### Surface Hierarchy & Nesting
Treat the UI as a series of stacked, premium materials. 
- Use `surface-container` (#e9edff) for the most interactive mid-ground elements.
- Use `surface-container-highest` (#d8e2ff) for active states or elevated "hero" cards.
- **The Glass & Gradient Rule:** For floating play-heads or media overlays, use `surface-variant` (#d8e2ff) with a 60% opacity and a `20px` backdrop-blur. Main Action buttons should use a subtle vertical gradient from `primary` (#004ced) to `primary_dim` (#0042d1) to provide "soul" and weight.

---

## 3. Typography
The system pairs two distinct sans-serifs to create an "Editorial Operational" feel.

- **The Voice (Manrope):** Used for `display` and `headline` scales. It is wide and authoritative. Use `headline-md` (1.75rem) for project titles to establish a "studio header" feel.
- **The Engine (Inter):** Used for `title`, `body`, and `label` scales. It is compact and neutral. 
- **Script Handling:** For long-form scripts, use `body-lg` with a custom line-height of `1.6` to ensure readability during the creative process.
- **Metadata:** Use `label-sm` (0.6875rem) in `on-surface-variant` (#455f90) for all technical data (timestamps, file sizes, frame rates).

---

## 4. Elevation & Depth
We achieve hierarchy through **Tonal Layering**, not shadows.

- **The Layering Principle:** To make a Media Card pop, place a `surface-container-lowest` (#ffffff) card on a `surface-container-low` (#f1f3ff) background. This creates a "soft lift."
- **Ambient Shadows:** Only use shadows for floating modals or context menus. Use a blur of `32px`, an opacity of `6%`, and tint the shadow with `on-surface` (#143161) to keep the light feeling natural and atmospheric.
- **The "Ghost Border" Fallback:** If a divider is required for accessibility in a dense table, use `outline-variant` (#99b2e9) at **15% opacity**. It should be felt, not seen.

---

## 5. Component Guidelines

### Media Cards & Artifact Headers
*   **Card Anatomy:** No borders. Use `surface-container-lowest` for the card body. Use `xl` (0.75rem) roundedness for the media thumbnail, but `md` (0.375rem) for the card itself. This "nested rounding" creates a custom, professional look.
*   **Forbid Dividers:** Do not use lines between list items. Use **Spacing Scale 4** (0.9rem) to create clear vertical separation.

### Status Badges (Semantic Precision)
*   **Approved:** `on_secondary_container` text on `secondary_container` background.
*   **Error:** `on_error_container` (#782232) text on `error_container` (#ff8b9a).
*   **Format:** All caps, `label-sm`, letter-spacing `0.05rem`.

### Buttons
*   **Primary:** `primary` (#004ced) background. Roundedness `md` (0.375rem). No shadow.
*   **Secondary:** `surface-container-high` (#e0e8ff) background with `on_surface` text. This blends the button into the "studio" environment.

### Density-Optimized Tables (Script/Timeline View)
*   Use `body-sm` for row data. 
*   Alternate row backgrounds between `surface` and `surface-container-low` instead of using lines.
*   Pin the first column (Artifact ID) using a `surface-bright` highlight.

### The Timeline List
A bespoke component for reels. Each "clip" in the list should be a `surface-container-highest` block with a `2px` left-accent of `primary` to indicate the active playhead position.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use white space as a structural element. If a section feels cluttered, increase the spacing to `Scale 8` or `10`.
*   **Do** use `inverse_surface` (#060e1e) for very small, high-contrast tooltips to provide a "darkroom" feel.
*   **Do** align metadata to a strict baseline grid to maintain the "operational" studio look.

### Don't
*   **Don't** use pure black (#000000). Use `inverse_surface` for dark elements to maintain the blue-toned neutral harmony.
*   **Don't** use standard "drop shadows" with 20%+ opacity. They look "cheap SaaS."
*   **Don't** use icons as the primary way to communicate status. Pair them with typography to maintain the editorial tone.
*   **Don't** use `DEFAULT` roundedness for large containers; reserve `lg` or `xl` for top-level cards to soften the studio atmosphere.
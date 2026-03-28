# Visual Consistency And Asset Memory

## Why This Document Exists

Maintaining visual continuity across a multi-clip short-form reel is the hardest technical problem on this platform. Each scene is generated independently unless the platform deliberately passes forward approved visual context.

This document defines the continuity model, the asset memory system, and how both feed into the generation pipeline.

## The Continuity Problem

When a 60-120 second reel is split into 5-8 second scene segments:

- Each image or video generation call receives only a text prompt unless the system deliberately passes reference context.
- Without reference anchoring, the same described character will appear differently across scenes.
- Even minor prompt variation compounds over multiple scenes, creating visual incoherence.

The solution is not to rely on model behavior for continuity. It is to enforce continuity through the platform's own data structures, stored references, and prompt construction.

## Consistency Pack

A consistency pack is the set of approved references and parameters that must be attached to every generation call for a given project or character.

### Consistency Pack Components

| Component | Description |
| --- | --- |
| `reference_images` | Approved images used as visual anchors |
| `character_sheet` | Structured text describing appearance |
| `style_descriptor` | Color palette, lighting style, lens type, mood, era |
| `negative_prompt` | Explicit exclusions to prevent unwanted variation |
| `seed_family` | A defined seed range or fixed seed used for reproducible generation attempts |
| `camera_defaults` | Default framing, aspect ratio, shot distance |
| `prompt_prefix` | A shared opening clause prepended to every visual generation prompt |

## Frame-Pair Continuity Chain

The platform now uses a frame-pair model per scene:

- `scene_start_frame`
- `scene_end_frame`

Continuity is enforced by chaining scenes together:

- Scene 1 start frame uses the consistency pack only.
- Scene 1 end frame references scene 1 start frame.
- Scene `N` start frame references scene `N-1` end frame plus the consistency pack.
- Scene `N` end frame references scene `N` start frame plus the consistency pack.

This means visual continuity is both:

- global, through the consistency pack
- local, through the previous scene's approved end frame

## Asset Memory Model

Asset memory is the project-scoped record of all generation inputs and outputs that the system uses to maintain continuity across steps and re-renders.

### Key Asset Memory Records

- `consistency_packs`
- approved start frames and end frames per scene
- chain edges linking `scene N end -> scene N+1 start`
- prompt snapshots stored on provider runs
- voice memory for narration continuity
- music reference for project-level audio continuity

## Storage Layout Extension

```text
workspace/{workspace_id}/project/{project_id}/
  consistency/
    pack.json
    reference_images/
    character_sheets/
  assets/
    images/
      start/
      end/
    videos/
      raw/
      silent/
      retimed/
```

## Generation Prompt Construction

Every image generation request must be assembled in this order:

1. global prompt prefix from the consistency pack
2. scene-specific narration context
3. scene-specific visual prompt
4. scene-specific start or end frame prompt
5. style descriptor from the visual preset
6. camera and framing instruction
7. previous scene's approved end frame reference when required
8. negative prompt from the consistency pack

The platform must never pass a raw user-written prompt directly to a provider adapter.

## Video Generation Priority

Whenever an approved frame pair exists for a scene, the generation pipeline must prefer first/last-frame or start/end-frame video generation over text-to-video. If the provider only supports single-image I2V, the approved start frame is used and the provider run is marked as degraded continuity mode.

## Frame-Pair Review Step

After frame-pair generation but before video generation, the platform must offer a frame-pair review step where the user can:

- accept the generated start and end frames
- regenerate the frame pair with adjusted prompt parameters
- replace an individual frame with an uploaded reference image

If a frame pair is changed for scene `N`, all later chained scenes are marked stale and require regeneration.

## Visual Continuity Score (Phase 5 Forward)

In Phase 5, the platform should introduce an optional automated continuity score that compares:

- embedding distance between successive scene end and next scene start frames
- color histogram similarity across scene images
- CLIP-style coherence between generated images and the approved reference set

## Failure Handling

- If the consistency pack is missing or incomplete when a generation step begins, the step must fail with `consistency_pack_required`.
- If a required chain reference has expired or been deleted, the system must warn the user and offer to regenerate or re-upload before proceeding.
- Prompt construction failures must be treated as deterministic errors and must not retry automatically.
- Changing an earlier scene in the chain must never silently preserve later scenes that are now continuity-invalid.

## Interaction With Provider Abstraction

The consistency pack is a platform-native concept. Each provider adapter is responsible for translating pack components and chain references into provider-specific parameters:

- image providers with ordered reference-image input receive the current scene reference set in order
- video providers with first/last-frame support receive both approved scene frames
- providers without those capabilities degrade to the best compatible mode and record the loss of fidelity in the provider run

## Implementation Phasing

| Phase | Continuity Work |
| --- | --- |
| Phase 1 | Define consistency pack schema in the database even if not yet populated |
| Phase 2 | Allow users to define visual presets and prompt pairs; store character sheets |
| Phase 3 | Enforce chained frame-pair usage in image and video generation; implement frame-pair review |
| Phase 5 | Introduce continuity scoring and lineage views showing how approved references were used |

# Phase 2 Overview: Content Planning

## Objective

Convert scripts into a structured, editable, approval-based scene plan that is ready for later asset generation.

## Why This Phase Exists

This is the phase that turns the platform from a text assistant into a controllable production system. It is where pacing, scene boundaries, visual instructions, and reusable presets become explicit instead of implicit.

## In Scope

- Script segmentation into timing-safe scene units
- Scene plan generation
- Visual presets
- Voice presets
- Scene-level editing
- Approval workflow for scripts and scene plans
- Draft versus approved planning versions

## Out Of Scope

- Final media generation
- Billing and usage controls
- Team review workflows beyond simple approvals

## What Users Get

- A scene-by-scene workflow between script and rendering
- Better control over pacing and prompts
- Reusable style and voice setup
- An approval checkpoint before expensive generation work begins

## Deliverables

- Scene plan domain model
- Segmentation engine and timing estimates
- Visual and voice preset management
- Scene planning UI with edit and approve actions
- Scene plan generation worker

## Exit Criteria

- Users can split scripts into scenes and adjust them manually
- Users can create and reuse presets
- One approved scene plan is available as a stable input for Phase 3 renders


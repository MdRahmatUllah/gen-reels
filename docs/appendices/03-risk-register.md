# Risk Register

## Product Risks

- Users may expect one-click perfect quality, while the product will still require retries and approvals.
- The workflow can feel too long if planning steps are not clearly justified and reusable.
- Heavy credits pricing can hurt adoption if value is not obvious before the first successful export.

## Technical Risks

- Visual continuity drift remains the most significant platform risk.
- Chained frame generation increases the chance that one bad scene invalidates downstream work.
- Video generation quality and latency may vary too much across providers.
- Inadequate checkpointing can make partial failures feel catastrophic.
- FFmpeg version compatibility across deployment environments can cause subtle output differences.
- Provider-returned clip audio may leak into final exports if source-audio stripping is skipped or misconfigured.
- Excessive clip retiming can create unnatural motion artifacts on short scenes.
- Providers without first/last-frame support may force degraded continuity mode.

## Operational Risks

- Queue backlogs can degrade user trust quickly.
- Billing and usage reconciliation failures can create customer support issues and incorrect charges.
- Provider outages can block renders if fallback rules are naive or absent.
- Provider rate limit stacking can stall the generation queue.
- Open-source model licenses or deployment requirements may be misunderstood if not tracked explicitly.

## Mitigations Summary

- Keep the launch promise narrow and workflow-centered.
- Track provider cost and latency from the first production render.
- Require immutable approved inputs before final rendering.
- Treat visual continuity as a first-class platform concern.
- Pin FFmpeg versions in container images and test composition in CI.
- Strip or suppress provider-returned clip audio before final composition.

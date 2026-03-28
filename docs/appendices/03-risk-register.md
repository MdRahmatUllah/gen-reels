# Risk Register

## Product Risks

- Users may expect one-click perfect quality, while the product will still require retries and approvals.
- The workflow can feel too long if planning steps are not clearly justified and reusable.
- Heavy credits pricing can hurt adoption if value is not obvious before the first successful export.

## Technical Risks

- **Visual consistency drift** is the most technically significant risk on this platform. Individual scene images and video clips are generated independently. Without explicit reference enforcement through the consistency pack system, character appearance, color grading, and environment details will vary noticeably between scenes. This risk is present in every render that includes a named character or a defined visual style. Mitigation: enforce consistency pack resolution before any generation step, use image-to-video (not text-to-video) wherever an approved keyframe exists, and introduce automated consistency scoring in Phase 5.
- Video generation quality and latency may vary too much across providers, making output feel inconsistent even within one project. Mitigation: evaluate providers systematically before launch; establish a performance baseline for each modality.
- Inadequate checkpointing can make partial failures feel catastrophic. Mitigation: model every render step as independently resumable from Phase 3.
- Provider abstractions can become leaky if adapters are not tightly controlled. Mitigation: enforce the adapter interface contract through automated tests on every adapter.
- Asset storage can become expensive or disorganized without retention rules. Mitigation: define retention windows per plan tier in Phase 4.
- **FFmpeg version compatibility** across deployment environments can cause subtle output differences (codec behavior, filter syntax, container format handling) that are hard to detect in CI and surface only in production exports. Mitigation: pin the FFmpeg version in the composition worker container image; run composition integration tests against the pinned binary in CI.

## Operational Risks

- Queue backlogs can degrade user trust quickly. Mitigation: scale on queue depth, not CPU; set a maximum queue wait SLO of 60 seconds.
- Billing and usage reconciliation failures can create customer support issues and incorrect charges. Mitigation: run the `reconcile_usage_vs_billing` job hourly; treat reconciliation discrepancies as alertable incidents.
- Provider outages can block renders if fallback rules are naive or absent. Mitigation: define and test fallback routes before launch; implement provider health checks in the orchestration layer.
- **Provider rate limit stacking**: if multiple workspaces trigger render jobs simultaneously and all route to the same provider, the platform can collectively exhaust the provider's rate limits, stalling the entire generation queue. Mitigation: implement per-provider rate limit tracking in Redis; queue generation steps with backoff when the platform-level provider rate limit is near exhaustion, before provider errors are returned.

## Security Risks

- BYO credentials create new secret handling and audit requirements. Mitigation: store BYO credentials with KMS envelope encryption; audit every credential access.
- Generated assets may expose sensitive content if storage permissions are misconfigured. Mitigation: all buckets are private; all access is via signed URLs with short TTL.
- User-uploaded assets introduce malware and moderation concerns in later phases. Mitigation: validate file type and size before issuing upload URLs; run moderation on uploads immediately after upload completes.

## Commercial Risks

- Margins can collapse if pricing is not aligned with video generation cost. Mitigation: capture cost per provider run from the first staging render; establish margin thresholds before public launch.
- Users may demand too many providers too early, increasing engineering cost without increasing conversion. Mitigation: use one primary provider per modality in early phases; defer provider expansion until Phase 4 reliability is established.
- Local execution features can distract the team before the hosted product is stable. Mitigation: defer Phase 7 until Phase 4 exit criteria are met and hosted usage accounting is trusted.

## Mitigations Summary

- Keep the launch promise narrow and workflow-centered.
- Track provider cost and latency from the first production render.
- Require immutable approved inputs before final rendering.
- Separate creator MVP success criteria from later studio and local execution goals.
- Treat visual consistency as a first-class platform concern, not a prompt engineering problem.
- Pin FFmpeg versions in container images and test composition in CI.
- Monitor provider rate limit consumption at the platform level before individual provider errors surface.



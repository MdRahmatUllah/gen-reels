# Roadmap And Phase Index

This roadmap is intentionally staged so the platform becomes usable early, but the architecture remains ready for broader studio requirements later.

## Phase Summary

| Phase | Name | Main Goal | What Users Get | Exit Signal |
| --- | --- | --- | --- | --- |
| 1 | Foundation | Establish product skeleton and project lifecycle | Auth, workspaces, briefs, idea generation, script generation, saved drafts, input moderation, and baseline rate limiting | Teams can create projects and generate editable scripts safely |
| 2 | Content Planning | Turn scripts into a controllable pre-render workflow | Scene segmentation, scene plans, style presets, voice presets, approval gates | Users can prepare a render-ready plan without generating media yet |
| 3 | Render MVP | Deliver end-to-end reel generation | Image and video generation, narration, keyframe review, preview renders, assembly, export library, and output moderation | Users can generate and download a controlled vertical reel |
| 4 | Reliability And Billing | Make rendering commercially operable | Checkpointing, retries, usage ledger, credits, admin queue visibility, moderation review queue | Renders are recoverable and usage is billable |
| 5 | Polish And Creator Productivity | Improve publish-readiness and iteration speed | Subtitles, templates, asset library, better audio and export polish, consistency scoring | Creators can reuse winning setups and publish faster |
| 6 | Collaboration And Studio | Support teams and brand operations | Roles, approvals, shared templates, brand kits, webhooks, API keys, auditability | Agencies and internal teams can collaborate in one workspace |
| 7 | Local And BYO Expansion | Add flexible execution models | BYO keys, local workers, routing policies, hybrid generation, worker health visibility | Advanced users can reduce cost and choose execution modes |

## Delivery Logic

- Phase 1 and Phase 2 separate planning from rendering so the product gains a usable workflow before high-cost generation.
- Phase 3 introduces end-to-end rendering only after the platform can version scripts, plans, and assets.
- Phase 4 protects gross margin and operational stability.
- Phase 5 improves creator retention through reusable templates and better outputs.
- Phase 6 expands the market.
- Phase 7 lowers cost and unlocks power-user flexibility.

## Cross-Phase Themes

- Versioning: every script, scene plan, preset, and export is versioned.
- Async orchestration: long-running work lives in background jobs, not request-response APIs.
- Cost visibility: provider usage and asset generation are tracked from the first production render.
- Controlled extensibility: provider adapters and worker contracts should allow later swap-outs without rewriting the product flow.
- Safety by default: moderation, auth, and quota controls are part of the platform foundation rather than post-launch patches.
- Consistency as a platform concern: visual consistency and asset memory are enforced by system design, not left to end users.

## Recommended Implementation Sequence

1. Finalize cross-cutting architecture documents.
2. Implement shared domain models and job contracts.
3. Build Phase 1 through Phase 3 in sequence with limited overlap.
4. Introduce billing and reliability before scaling acquisition.
5. Layer in creator polish, then team features, then hybrid execution.

## Phase Dependencies

- Phase 2 depends on Phase 1 project, script, and draft versioning.
- Phase 3 depends on Phase 2 scene plans and approval state.
- Phase 4 depends on Phase 3 render jobs, provider telemetry, and moderation outcomes.
- Phase 5 depends on stable render outputs and asset histories.
- Phase 6 depends on mature workspace and project ownership models plus notification infrastructure.
- Phase 7 depends on solid provider abstraction and usage governance.

## What To Review Before Starting Any Phase

- Relevant top-level architecture docs
- The prior phase overview and exit criteria
- Appendix glossary and API catalog
- Decision log for any changed assumptions

# Reels Generation Platform Documentation

This documentation package turns the idea and discussion notes in this folder into a build-ready, modular plan for a creator-first video generation platform with a React frontend and FastAPI backend.

## Product Direction

- Launch shape: hybrid SaaS with hosted infrastructure first.
- Initial target user: faceless content creators producing 9:16 short-form video in the 60-120 second range.
- Expansion path: agencies, studio teams, collaboration, and local or bring-your-own-provider execution.
- Commercial guardrail: video generation is a metered product, not an unlimited feature.

## Core Technical Direction

- Frontend: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, and a reusable component library.
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, Celery, and Redis.
- Data layer: PostgreSQL for domain data and MinIO-backed S3-compatible object storage for media assets.
- Media pipeline: provider adapters for text, image, video, and narration services plus FFmpeg-based assembly workers.
- Render model: idea selection, 5-8 second scene segmentation, prompt pairs, chained start/end frame generation, silent clip normalization, narration sync, and FFmpeg-based final export.
- Operations: job-based asynchronous orchestration, checkpointing, retries, resumability, and usage telemetry.

## Reference Stack

- Hosted text and image path: Azure OpenAI plus reference-aware image providers such as Gemini 2.5 Flash Image ("nano banana") through provider adapters.
- Hosted video path: Veo 3.1 class provider for first/last-frame video generation.
- Hosted narration path: Azure OpenAI TTS class provider.
- Local or BYO path: open-source image, video, and TTS models behind the same adapter contracts.
- Storage and containers: MinIO and Docker in local development, with production deployment retaining the same logical service split.

## Reading Order

### Core Documents

1. [Project Overview](./01-project-overview.md)
2. [Roadmap And Phase Index](./02-roadmap-and-phase-index.md)

### Architecture Documents

3. [System Context](./architecture/01-system-context.md)
4. [Frontend Architecture](./architecture/02-react-frontend-architecture.md)
5. [Backend Architecture](./architecture/03-fastapi-backend-architecture.md)
6. [Data Model And Storage](./architecture/04-data-model-and-storage.md)
7. [Job Orchestration And Render Pipeline](./architecture/05-job-orchestration-and-render-pipeline.md)
8. [Provider Abstraction And Integration Architecture](./architecture/06-provider-abstraction-and-integration-architecture.md)
9. [Deployment, Observability, And Security](./architecture/07-deployment-observability-and-security.md)
10. [Visual Consistency And Asset Memory](./architecture/08-visual-consistency-and-asset-memory.md)
11. [Content Moderation And Safety](./architecture/09-content-moderation-and-safety.md)
12. [Notifications And Webhooks](./architecture/10-notifications-and-webhooks.md)
13. [Rate Limiting And Quota Enforcement](./architecture/11-rate-limiting-and-quota-enforcement.md)
14. [Authentication And Identity](./architecture/12-authentication-and-identity.md)
15. [Local Worker Agent Protocol](./architecture/13-local-worker-agent-protocol.md)
16. [Composition And Audio-Visual Consistency](./architecture/14-composition-and-av-consistency.md)
17. [Scene Frame Pair And Reference Chain](./architecture/15-scene-frame-pair-and-reference-chain.md)
18. [Containerization And Docker Strategy](./architecture/16-containerization-and-docker-strategy.md)
19. [MinIO Storage Configuration](./architecture/17-minio-storage-configuration.md)

### Phase Documents

20. Phase folders under `docs/phases`

### Appendices

21. Appendices under `docs/appendices`

## Folder Layout

```text
docs/
  README.md
  01-project-overview.md
  02-roadmap-and-phase-index.md
  architecture/
    01-system-context.md
    02-react-frontend-architecture.md
    03-fastapi-backend-architecture.md
    04-data-model-and-storage.md
    05-job-orchestration-and-render-pipeline.md
    06-provider-abstraction-and-integration-architecture.md
    07-deployment-observability-and-security.md
    08-visual-consistency-and-asset-memory.md
    09-content-moderation-and-safety.md
    10-notifications-and-webhooks.md
    11-rate-limiting-and-quota-enforcement.md
    12-authentication-and-identity.md
    13-local-worker-agent-protocol.md
    14-composition-and-av-consistency.md
    15-scene-frame-pair-and-reference-chain.md
    16-containerization-and-docker-strategy.md
    17-minio-storage-configuration.md
  phases/
    phase-1-foundation/
    phase-2-content-planning/
    phase-3-render-mvp/
    phase-4-reliability-and-billing/
    phase-5-polish-and-creator-productivity/
    phase-6-collaboration-and-studio/
    phase-7-local-and-byo-expansion/
  appendices/
    01-api-surface-and-endpoint-catalog.md
    02-domain-glossary.md
    03-risk-register.md
    04-decision-log.md
    05-provider-capability-matrix.md
    06-python-media-tooling-and-service-selection.md
```

## How To Use These Docs

- Use the top-level overview and architecture documents as the source of truth for cross-cutting decisions.
- Use each phase folder to scope delivery, estimate work, and hand off implementation slices.
- Use the appendices when building APIs, defining schemas, reviewing provider capability, or checking tooling decisions.
- Keep the earlier `project-idea.md` and `discussion-*.md` files as raw source notes, not the final specification.

## Priority Reading Before Coding Begins

Before any team member writes production code, these documents must be read in full:

1. `12-authentication-and-identity.md` - every API and session decision depends on this.
2. `08-visual-consistency-and-asset-memory.md` - the most technically complex platform concern.
3. `15-scene-frame-pair-and-reference-chain.md` - defines the start/end frame workflow and chained continuity rules.
4. `14-composition-and-av-consistency.md` - defines silent clip policy, retiming, music ducking, loudness, and voice continuity rules.
5. `04-data-model-and-storage.md` - the schema decisions constrain all other work.
6. `11-rate-limiting-and-quota-enforcement.md` - commercial viability depends on this being right from Phase 1.

## Documentation Standards

- Every phase has four files: `overview`, `architecture`, `implementation-plan`, and `integrations`.
- Every architecture document describes component boundaries, data flow, failure handling, and rollout implications.
- Every implementation plan should be actionable by frontend, backend, infra, and QA contributors without needing extra scoping.
- Every integration document names the integration type, credential model, contract shape, error strategy, and cost implications.
- Every decision that materially changes architecture, schema, provider selection, or pricing must be recorded in `04-decision-log.md` in the same change.

# System Context And Architecture

## Overview

The Reels Generation Platform is a service-oriented SAAS product. It is not a monolith. The first releases will ship as a small set of coordinated services — a web client, an API gateway, background workers, and storage — with the option to scale each layer independently as demand grows.

## System Context Diagram

```mermaid
graph TB
    Creator["Creator / User"] -- HTTPS --> WebApp["React Web App"]
    WebApp -- REST / SSE --> API["FastAPI API Service"]
    API -- "Read/Write" --> DB["PostgreSQL"]
    API -- "Enqueue Jobs" --> Broker["Redis (Celery Broker)"]
    Broker -- "Dispatch" --> Workers["Celery Workers"]
    Workers -- "Direct Write" --> DB
    Workers -- "Read/Write Assets" --> Storage["MinIO\n(S3-Compatible)"]
    Workers -- "Generate" --> Providers["Generation Providers"]
    API -- "Signed URL" --> Storage
    
    subgraph Providers["Generation Providers"]
        AzureOpenAI["Azure OpenAI\n(Image, TTS, Text)"]
        Veo3["Veo 3 / Vertex AI\n(Video FLF2V / I2V)"]
        OpenSource["Open-Source Models\n(Wan2.1, FLUX, XTTSv2)\nvia Docker + GPU"]
    end

    subgraph Infrastructure["Infrastructure"]
        Docker["Docker Containers"]
        Compose["Docker Compose\n(Local Dev)"]
    end
```

## Service Decomposition

| Service | Technology | Purpose |
|---|---|---|
| **Web App** | React, TypeScript, Vite, Tailwind CSS | Creator-facing UI |
| **API Service** | FastAPI, Pydantic, SQLAlchemy | REST endpoints, domain operations, job submission |
| **Workers** | Celery, Redis | Async generation jobs, composition, audio strip, duration alignment |
| **Database** | PostgreSQL | Domain data, workflow state, usage records |
| **Object Storage** | MinIO (S3-compatible) | Media assets, exports, quarantine, model weights |
| **Broker** | Redis | Celery message broker, SSE buffer, rate limit state, cache |
| **Composition Worker** | FFmpeg, ffmpeg-python | Video assembly, audio stripping, speed-matching, loudness normalisation |
| **GPU Workers** | Docker + CUDA | Self-hosted open-source model inference (Wan2.1, FLUX, XTTSv2) |

## Core Data / Control Flow

```mermaid
sequenceDiagram
    participant U as Creator
    participant W as Web App
    participant A as API
    participant Q as Redis / Celery
    participant WK as Worker
    participant P as Provider (Azure / Veo3 / OSS)
    participant DB as PostgreSQL
    participant S as MinIO

    U->>W: Create project, define brief
    W->>A: POST /projects + brief
    A->>DB: Store project, brief
    U->>W: Generate viral ideas
    W->>A: POST /ideas:generate
    A->>Q: Enqueue idea generation job
    Q->>WK: Dispatch to text worker
    WK->>P: Call text provider (Azure OpenAI)
    P-->>WK: Return idea set
    WK->>DB: Store idea set
    U->>W: Select idea
    W->>A: POST /ideas/{id}:select
    U->>W: Generate script (60-120s)
    W->>A: POST /scripts:generate
    A->>Q: Enqueue script generation
    Q->>WK: Dispatch
    WK->>P: Call text provider
    P-->>WK: Return script
    WK->>DB: Store script version
    U->>W: Approve script, segment, generate prompt pairs
    Note over WK: Scene segmentation + prompt pair generation
    U->>W: Start render
    W->>A: POST /renders
    A->>DB: Create render job, snapshot consistency pack
    A->>Q: Enqueue paired image generation (sequential chain)
    Note over WK: Scene 1: start frame (pack only)
    WK->>P: Generate start frame
    P-->>WK: Start frame image
    WK->>S: Store start frame
    Note over WK: Scene 1: end frame (start frame ref)
    WK->>P: Generate end frame
    P-->>WK: End frame image
    WK->>S: Store end frame
    Note over WK: Scene 2: start frame (scene 1 end frame ref)
    WK->>P: Generate start frame (chained)
    Note over WK: ...repeat for all scenes...
    WK->>DB: Update step statuses
    Note over U: Frame pair review gate
    U->>W: Approve frame pairs
    W->>A: POST /steps/{id}:approve-frame-pair
    A->>Q: Enqueue video generation per scene
    WK->>P: FLF2V video generation (start + end frames)
    P-->>WK: Video clip (silent)
    WK->>S: Store video clip
    Note over WK: Audio strip + narration + duration alignment
    WK->>S: Store processed clips
    Note over WK: Composition
    WK->>S: Store final export
    WK->>DB: Mark render complete
    U->>W: Download export
    W->>A: GET signed URL
    A->>S: Generate pre-signed URL
```

## The Worker Write Path

The architecture uses a **direct write path** for workers: workers write their results directly to PostgreSQL and MinIO without routing through the API service. This avoids creating a bottleneck at the API layer during heavy generation workloads.

Rules:
- Workers open their own database sessions (sync, managed directly by worker code, not FastAPI's `Depends`).
- Workers use the MinIO/S3 SDK directly for asset storage.
- Workers never call API endpoints to report results — they write directly to the database.
- The API reads the same database tables to serve status queries to the frontend.
- SSE events are published by workers to Redis and consumed by the API for delivery to connected clients.

## Deployment Units

| Unit | Container | GPU Required | Autoscaling Signal |
|---|---|---|---|
| Web App | `reels-frontend` | No | Request rate |
| API Service | `reels-api` | No | Request rate / connection count |
| Planning Workers | `reels-worker-planning` | No | Queue depth (planning queue) |
| Image Generation Workers | `reels-worker-image` | Optional (GPU for open-source) | Queue depth (image queue) |
| Video Generation Workers | `reels-worker-video` | Yes (for open-source models) | Queue depth (video queue) |
| Audio / TTS Workers | `reels-worker-audio` | Optional | Queue depth (audio queue) |
| Composition Workers | `reels-worker-composition` | No | Queue depth (composition queue) |
| PostgreSQL | `reels-postgres` | No | N/A (managed or single instance) |
| Redis | `reels-redis` | No | N/A |
| MinIO | `reels-minio` | No | N/A |

## Key Constraints

- **Sequential image generation:** Frame pair generation is sequential across scenes due to reference chaining. Scene N depends on scene N-1's end frame. This is an architectural constraint, not a performance bug.
- **Provider audio policy:** Video generation must always request silent output or strip audio post-generation. Provider-generated audio must never reach the composition pipeline.
- **Consistency pack snapshot:** Every render job captures its consistency pack at creation time. Workers always read the snapshot, never the live pack.
- **Signed URLs for all asset access:** No direct public URLs for any stored assets. All client-facing URLs are pre-signed with short TTL.

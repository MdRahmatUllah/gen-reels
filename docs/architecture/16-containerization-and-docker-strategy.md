# Containerization And Docker Strategy

## Purpose

This document defines the platform's containerization approach. Docker is the standard deployment and development environment for all services. Docker Compose provides the local development orchestration layer.

---

## Container Inventory

| Container | Base Image | GPU Required | Purpose |
|---|---|---|---|
| `reels-frontend` | `node:20-alpine` | No | React web application (Vite dev server or Nginx for production) |
| `reels-api` | `python:3.12-slim` | No | FastAPI application |
| `reels-worker-planning` | `python:3.12-slim` | No | Celery workers for idea, script, and scene planning tasks |
| `reels-worker-image` | `python:3.12-slim` | Optional | Celery workers for image generation (GPU for open-source models) |
| `reels-worker-video` | `python:3.12-slim` / `nvidia/cuda:12.x` | Yes (open-source) | Celery workers for video generation |
| `reels-worker-audio` | `python:3.12-slim` | Optional | Celery workers for TTS narration (GPU for open-source models) |
| `reels-worker-composition` | `python:3.12-slim` + FFmpeg | No | Celery workers for audio strip, duration alignment, and FFmpeg composition |
| `reels-beat` | `python:3.12-slim` | No | Celery Beat scheduler |
| `reels-postgres` | `postgres:16-alpine` | No | PostgreSQL database |
| `reels-redis` | `redis:7-alpine` | No | Celery broker, SSE buffer, cache |
| `reels-minio` | `minio/minio:latest` | No | S3-compatible object storage |

### GPU Worker Containers

GPU workers for open-source model inference (Wan2.1, FLUX, XTTSv2) use NVIDIA CUDA base images:

```dockerfile
# Example: Wan2.1 video generation worker
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3.12 python3-pip ffmpeg
COPY requirements-gpu.txt .
RUN pip install -r requirements-gpu.txt

# Model weights are volume-mounted, not baked into the image
VOLUME /models

COPY . /app
WORKDIR /app
CMD ["celery", "-A", "workers", "worker", "-Q", "video_generation", "--concurrency=1"]
```

**Key rule:** Model weights are **volume-mounted**, never baked into container images. This keeps images small (< 2GB) and allows model updates without rebuilding.

---

## Docker Compose: Local Development

```yaml
# docker-compose.yml (simplified structure)
version: "3.9"

services:
  frontend:
    build: ./apps/web
    ports: ["3000:3000"]
    volumes: ["./apps/web/src:/app/src"]
    environment:
      VITE_API_URL: http://localhost:8000

  api:
    build: ./apps/api
    ports: ["8000:8000"]
    volumes: ["./apps/api:/app"]
    depends_on: [postgres, redis, minio]
    environment:
      DATABASE_URL: postgresql://reels:reels@postgres:5432/reels
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin

  worker-planning:
    build: ./apps/worker
    command: celery -A workers worker -Q planning --concurrency=4
    volumes: ["./apps/worker:/app"]
    depends_on: [postgres, redis, minio]

  worker-media:
    build: ./apps/worker
    command: celery -A workers worker -Q image_generation,video_generation,audio_generation --concurrency=2
    volumes: ["./apps/worker:/app"]
    depends_on: [postgres, redis, minio]

  worker-composition:
    build:
      context: ./apps/worker
      dockerfile: Dockerfile.composition
    command: celery -A workers worker -Q audio_strip,duration_alignment,composition --concurrency=2
    volumes: ["./apps/worker:/app"]
    depends_on: [postgres, redis, minio]

  beat:
    build: ./apps/worker
    command: celery -A workers beat --loglevel=info
    depends_on: [redis]

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: reels
      POSTGRES_PASSWORD: reels
      POSTGRES_DB: reels
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"   # API
      - "9001:9001"   # Console
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes: ["minio_data:/data"]

volumes:
  postgres_data:
  minio_data:
```

### GPU Workers (Optional Compose Override)

```yaml
# docker-compose.gpu.yml
version: "3.9"

services:
  worker-video-gpu:
    build:
      context: ./apps/worker
      dockerfile: Dockerfile.gpu
    command: celery -A workers worker -Q video_generation --concurrency=1
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - ./models:/models:ro
      - ./apps/worker:/app
    depends_on: [postgres, redis, minio]
```

Run with: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`

---

## Dockerfile Standards

### Application Services (API, Workers)

```dockerfile
FROM python:3.12-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
```

### Composition Worker (FFmpeg)

```dockerfile
FROM python:3.12-slim AS base

# FFmpeg is a hard dependency for composition
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-composition.txt .
RUN pip install --no-cache-dir -r requirements-composition.txt
COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
```

### Frontend

```dockerfile
# Development
FROM node:20-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]

# Production (multi-stage)
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

---

## Image Tagging Strategy

| Environment | Tag Format | Example |
|---|---|---|
| Local development | `latest` | `reels-api:latest` |
| CI/CD builds | Git commit SHA | `reels-api:a1b2c3d` |
| Staging | Commit SHA + `staging` | `reels-api:a1b2c3d-staging` |
| Production | Commit SHA (never `latest`) | `reels-api:a1b2c3d` |

**Rule:** Production images are never tagged `latest`. All production deployments reference an immutable commit-SHA-tagged image.

---

## Volume Strategy

| Volume | Mount Point | Purpose | Persistence |
|---|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | Database files | Persistent (named volume) |
| `minio_data` | `/data` | Object storage data | Persistent (named volume) |
| `./models` | `/models` (read-only) | Open-source model weights | Host-mounted, read-only |
| Application source | `/app` | Hot-reload during development | Bind mount (dev only) |

---

## Environment Variable Management

- **Local development:** `.env` file loaded by Docker Compose with `env_file:` directive.
- **Staging/Production:** Environment variables injected via orchestrator (Kubernetes, ECS) or secret manager.
- **Secrets:** Never stored in `.env` files in staging or production. Use Azure Key Vault or equivalent.
- **Required variables per service:** Documented in each service's `Dockerfile` or a `.env.example` file at the repo root.

---

## Health Checks

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U reels"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
```

---

## Networking

- All services communicate over a shared Docker Compose network (`reels-net`).
- Only `frontend` (3000), `api` (8000), and `minio` console (9001) expose ports to the host.
- Inter-service communication uses Docker DNS names (e.g., `postgres`, `redis`, `minio`).
- In production, a reverse proxy (Nginx, Traefik, or cloud load balancer) handles TLS termination and routes traffic to the API and frontend.

---

## Implementation Phasing

| Phase | Docker Work |
|---|---|
| Phase 1 | Docker Compose for API, frontend, PostgreSQL, Redis, MinIO. Basic `.env.example`. |
| Phase 3 | Composition worker Dockerfile with FFmpeg. Worker queue separation. |
| Phase 5 | CI/CD pipeline for image builds, tagging, and registry push. |
| Phase 7 | GPU worker Dockerfiles. `docker-compose.gpu.yml` override. Model weight volume mounts. |

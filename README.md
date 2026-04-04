# Reels Generation Platform

Reels Generation is a multi-stage platform for turning a brief into a short-form vertical video. The product flow covers idea generation, script writing, scene planning, frame-pair generation, video clips, narration, subtitles, music, and final composition.

This repository currently contains:

- a FastAPI backend with Celery workers, PostgreSQL, Redis, and MinIO integration
- a React + Vite frontend
- Docker-based local infrastructure under [infra](./infra)
- architecture and phase documentation under [docs](./docs)

## Repository Layout

```text
reels-generation/
  backend/
  frontend/
  infra/
  docs/
```

Useful entry points:

- [backend/README.md](./backend/README.md)
- [frontend/README.md](./frontend/README.md)
- [infra/README.md](./infra/README.md)
- [docs/README.md](./docs/README.md)

## Prerequisites

### For Docker-first usage

- Docker Desktop with Docker Compose v2

### For local development outside Docker

- Python `3.12+`
- `uv`
- Node.js `20+`
- npm

Install `uv` if needed:

```bash
pip install uv
```

## Fastest Way To Run The App

The recommended path is the full Docker stack from the repo root.

### 1. Start the stack

```bash
docker compose up --build
```

This starts:

- frontend
- API
- worker queues
- Celery beat
- PostgreSQL
- Redis
- MinIO
- Mailpit

### 2. Run migrations

In another terminal:

```bash
docker compose exec api uv run alembic upgrade head
```

### 3. Seed sample data

```bash
docker compose exec api uv run reels-cli seed
```

### 4. Open the app

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`
- Mailpit: `http://localhost:8025`

Seeded admin:

- email: `admin@example.com`
- password: `ChangeMe123!`

## Cloud Provider Credentials Vs Stub Mode

The backend can run in two useful development modes.

### Stub provider mode

Use this if you want local backend flows without Azure / Vertex credentials:

```bash
USE_STUB_PROVIDERS=true docker compose up --build
```

PowerShell:

```powershell
$env:USE_STUB_PROVIDERS = "true"
docker compose up --build
```

### Hosted provider mode

Use this if you want real provider-backed generation:

- Azure OpenAI for text, image, and speech
- Azure Content Safety for moderation
- Vertex / Veo for video generation

Set the relevant environment values from:

- [backend/.env.example](./backend/.env.example)
- [infra/env/backend.env](./infra/env/backend.env)

## Run Backend Locally

If you want to run the backend outside Docker while still using Docker for Postgres, Redis, MinIO, and Mailpit:

### 1. Start dependency services

```bash
docker compose -f infra/compose/docker-compose.yml up -d postgres redis minio minio-init mailpit
```

### 2. Prepare backend env

Create `backend/.env` from [backend/.env.example](./backend/.env.example).

For local development without cloud credentials, set:

```env
USE_STUB_PROVIDERS=true
```

### 3. Install backend dependencies

```bash
cd backend
uv sync --extra dev
```

### 4. Migrate and seed

```bash
uv run alembic upgrade head
uv run reels-cli seed
```

### 5. Start the API

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

More details are in [backend/README.md](./backend/README.md).

## Run Frontend Locally

### Mock-data mode

```bash
cd frontend
npm install
npm run dev
```

### Live backend mode

Create `frontend/.env.local`:

```env
VITE_API_MODE=live
VITE_API_URL=http://localhost:8000
```

Then run:

```bash
cd frontend
npm install
npm run dev
```

More details are in [frontend/README.md](./frontend/README.md).

## YouTube Publishing Local Setup

The YouTube publishing flow adds Google OAuth, a dedicated publishing worker queue, and live frontend screens under `Publishing`.

### Backend env additions

Add these values to `backend/.env`:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/integrations/youtube/callback
FRONTEND_URL=http://localhost:5173
YOUTUBE_SCOPES=openid,email,profile,https://www.googleapis.com/auth/youtube,https://www.googleapis.com/auth/youtube.upload
```

### Required local processes

For YouTube publishing you should run:

- FastAPI backend
- Redis
- Postgres
- Celery beat
- at least one worker for `audio`
- one worker for `publishing`

Manual worker examples:

```bash
cd backend
uv run celery -A app.workers.celery_app.celery_app worker -Q audio --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q publishing --loglevel=info
uv run celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

The Google Console setup steps are documented in [docs/manual-google-youtube-local-setup.md](./docs/manual-google-youtube-local-setup.md).

## Current Frontend Caveat

The frontend TypeScript build now passes in live mode. In this sandbox environment, `vite build` can still fail because `esbuild` process spawning is restricted, so validate a full production bundle on your local machine when needed. If you run:

```bash
cd frontend
npm run build
```

it may fail here because of sandbox `EPERM`, not necessarily because of project TypeScript errors. The earlier review is documented in [frontend-report.md](./frontend-report.md).

## Docker Commands

### Start everything

```bash
docker compose up --build
```

### Start in background

```bash
docker compose up -d --build
```

### Stop everything

```bash
docker compose down
```

### Stop and remove volumes

```bash
docker compose down -v
```

### Validate the Compose configuration

```bash
docker compose config -q
```

### Canonical infra commands

The root `docker-compose.yml` files are compatibility wrappers. The canonical files live under [infra/compose](./infra/compose):

```bash
docker compose -f infra/compose/docker-compose.yml up --build
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.gpu.yml up --build
```

## Optional Bootstrap Helpers

You can also use the infra bootstrap script:

PowerShell:

```powershell
./infra/scripts/bootstrap-local.ps1
```

Shell:

```bash
./infra/scripts/bootstrap-local.sh
```

These helpers:

- start the local stack
- run Alembic migrations
- seed sample data

## Troubleshooting

### `minio-init` exited

That is expected. It is a one-shot container that creates the required buckets and then stops successfully.

### MinIO warns about `minioadmin:minioadmin`

That is expected from the committed local defaults. It is acceptable for local development only. Override `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` for anything shared or production-like.

### The frontend is running but still shows mock data

Set:

```env
VITE_API_MODE=live
VITE_API_URL=http://localhost:8000
```

### The backend starts but generation calls fail

Either:

- enable `USE_STUB_PROVIDERS=true`, or
- configure the Azure and Vertex variables required by the backend

### Need a full reset

```bash
docker compose down -v
docker compose up --build
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run reels-cli seed
```

## Documentation

- Product and architecture docs: [docs/README.md](./docs/README.md)
- Infra details: [infra/README.md](./infra/README.md)
- Frontend implementation review: [frontend-report.md](./frontend-report.md)
- Google OAuth local setup: [docs/manual-google-youtube-local-setup.md](./docs/manual-google-youtube-local-setup.md)
- Publishing implementation plan: [docs/youtube-publishing-implementation-plan.md](./docs/youtube-publishing-implementation-plan.md)

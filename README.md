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

## Current Frontend Caveat

The frontend dev server works, but the production build still has outstanding TypeScript issues. If you run:

```bash
cd frontend
npm run build
```

it is expected to fail until the remaining frontend cleanup work is finished. The review is documented in [frontend-report.md](./frontend-report.md).

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

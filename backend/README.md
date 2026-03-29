# Backend

FastAPI control plane and worker runtime for the Reels Generation platform.

The backend owns:

- authentication and workspace context
- project, brief, idea, script, scene-plan, render, asset, billing, and collaboration APIs
- Celery workers and beat scheduling
- PostgreSQL persistence
- Redis-backed queues, rate limiting, and event streaming support
- MinIO-backed asset storage
- provider routing for hosted, BYO, and local-worker execution

## Stack

- Python `3.12+`
- FastAPI
- SQLAlchemy 2 + Alembic
- Celery + Redis
- PostgreSQL
- MinIO
- `uv` for dependency and command management

## What Works Today

The backend covers the documented multi-phase platform flow:

- auth and workspace selection
- projects, versioned briefs, ideas, scripts, scene plans, and presets
- render orchestration, events, notifications, usage, and billing
- review, comments, brand kits, templates, asset library, and workspace admin
- BYO credentials, local workers, execution policies, and routing

## Prerequisites

- Python `3.12+`
- `uv`
- Docker Desktop if you want local Postgres, Redis, MinIO, Mailpit, and the worker stack

Install `uv` if needed:

```bash
pip install uv
```

## Recommended Local Development

The easiest backend workflow is:

1. Start the infrastructure dependencies with Docker.
2. Run the API locally with `uv`.
3. Use stub providers until you have Azure and Vertex credentials.

### 1. Create `backend/.env`

Start from [`.env.example`](./.env.example).

For a quick local setup without cloud credentials, make sure these values are set:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://reels:reels@localhost:5432/reels
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
USE_STUB_PROVIDERS=true
```

Notes:

- In `development`, the app auto-generates JWT keys and the app encryption key if they are blank.
- If you want real provider calls, leave `USE_STUB_PROVIDERS=false` and fill the Azure / Vertex variables from [`.env.example`](./.env.example).

### 2. Start local dependencies

From the repo root:

```bash
docker compose -f infra/compose/docker-compose.yml up -d postgres redis minio minio-init mailpit
```

`minio-init` is a one-shot bootstrap container. It should exit successfully after creating buckets.

### 3. Install backend dependencies

```bash
cd backend
uv sync --extra dev
```

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Seed sample data

```bash
uv run reels-cli seed
```

Seeded admin:

- email: `admin@example.com`
- password: `ChangeMe123!`

### 6. Start the API

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend URLs:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/readyz`

## Running Workers

For full render and notification flow you also need workers and beat. The recommended way is Docker, but you can run them manually too.

Examples:

```bash
uv run celery -A app.workers.celery_app.celery_app worker -Q planning --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q frame --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q video --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q audio --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q composition --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q notifications --loglevel=info
uv run celery -A app.workers.celery_app.celery_app worker -Q maintenance --loglevel=info
uv run celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

Queues currently used by the backend:

- `planning`
- `frame`
- `video`
- `audio`
- `composition`
- `notifications`
- `maintenance`

## Full Docker Option

If you want the API, workers, beat, frontend, and all infra together, use the root wrapper from the repo root:

```bash
docker compose up --build
```

Then initialize the backend:

```bash
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run reels-cli seed
```

If you do not have cloud provider credentials yet, override provider mode for Docker:

```bash
USE_STUB_PROVIDERS=true docker compose up --build
```

On PowerShell:

```powershell
$env:USE_STUB_PROVIDERS = "true"
docker compose up --build
```

## Tests And Checks

Run the backend tests:

```bash
uv run pytest
```

Optional checks:

```bash
uv run ruff check .
python -m compileall app alembic
```

## Important Files

- [app/main.py](./app/main.py): FastAPI app, middleware, health, readiness
- [app/cli.py](./app/cli.py): seed CLI
- [app/workers/celery_app.py](./app/workers/celery_app.py): Celery queues and beat schedule
- [alembic.ini](./alembic.ini): Alembic config
- [.env.example](./.env.example): backend environment reference

## Troubleshooting

### `alembic upgrade head` fails against Postgres

Make sure your `DATABASE_URL` points at `postgres`, not `localhost`, when running inside Docker. For local non-Docker execution, `localhost` is correct.

### Backend starts but provider-backed generation fails

You are likely missing Azure / Vertex credentials. For local development, set:

```env
USE_STUB_PROVIDERS=true
```

### MinIO is running but `minio-init` stopped

That is expected. `minio-init` creates the buckets once, then exits successfully.

### Need a clean local reset

From the repo root:

```bash
docker compose down -v
docker compose up --build
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run reels-cli seed
```


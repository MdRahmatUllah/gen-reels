# Infra

`infra/` is the canonical home for local Docker orchestration, runtime images, env templates, and bootstrap scripts.

## Layout

- `compose/` contains the source-of-truth Compose files.
- `docker/` contains the backend and frontend Dockerfiles plus frontend Nginx config.
- `env/` contains the committed local env defaults and optional GPU override template.
- `scripts/` contains MinIO bootstrap and local startup helpers.

## Canonical Commands

Start the full local stack:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

Start with GPU and local-model services:

```bash
docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.gpu.yml up --build
```

Bootstrap the stack, run migrations, and seed sample data:

```powershell
./infra/scripts/bootstrap-local.ps1
```

## Env Loading

Compose loads env files in this order:

1. `infra/env/common.env`
2. `infra/env/backend.env` or `infra/env/frontend.env`

Shell environment variables still win over committed defaults. `infra/env/gpu.env.example` is an optional template for GPU or local-model overrides if you want to pass extra values with `docker compose --env-file`.

## Defaults

- Frontend runs in `live` API mode by default with `VITE_API_URL=http://localhost:8000`.
- The default stack uses the frontend `dev` target and Vite hot reload.
- The frontend `prod` target exists for static Nginx serving, but the current frontend build still depends on the pending TypeScript cleanup tracked in `frontend-report.md`.
- Root `docker-compose.yml` files remain compatibility wrappers; `infra/compose/` is the source of truth.


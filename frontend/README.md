# Frontend

React + TypeScript + Vite frontend for the Reels Generation platform.

The frontend implements the creator and studio workflow UI, including:

- login and shell layout
- dashboard and project library
- brief, script, scene, render, export, preset, template, asset, billing, review, and settings surfaces
- admin and workspace management views

## Stack

- React `19`
- TypeScript
- Vite
- React Router
- TanStack Query
- Zustand
- Tailwind CSS, with some legacy styling still being migrated

## Current State

The frontend is functionally broad, but two important caveats are still true:

1. Much of the app flow is still mock-data driven.
2. The production build currently has outstanding TypeScript issues, so `npm run build` is not clean yet.

For day-to-day UI development, `npm run dev` works. For architecture gaps and implementation findings, see [../frontend-report.md](../frontend-report.md).

## Prerequisites

- Node.js `20+`
- npm

## Install

```bash
cd frontend
npm install
```

## Run The Frontend

### Mock Mode

Mock mode is the easiest way to explore the UI without the backend:

```bash
npm run dev
```

Default local URL:

- `http://localhost:5173`

By default, the frontend falls back to:

- `VITE_API_MODE=mock`
- `VITE_API_URL=http://localhost:8000`

### Live Backend Mode

To point the frontend at the FastAPI backend, create `frontend/.env.local`:

```env
VITE_API_MODE=live
VITE_API_URL=http://localhost:8000
```

Then start the frontend:

```bash
npm run dev
```

## Docker Frontend

The Docker stack runs the frontend in live mode by default and serves the Vite dev server on:

- `http://localhost:5173`

From the repo root:

```bash
docker compose up --build
```

## Scripts

```bash
npm run dev
npm run build
npm run preview
```

Notes:

- `npm run dev` is the normal frontend workflow today.
- `npm run build` currently fails because of known TypeScript cleanup items.
- `npm run preview` is useful only after a successful build.

## Recommended Local Workflow

### Frontend only

Use mock mode:

```bash
cd frontend
npm install
npm run dev
```

### Frontend + local backend

1. Start the backend and local services from the repo root.
2. Set `VITE_API_MODE=live` and `VITE_API_URL=http://localhost:8000`.
3. Run the frontend dev server.

Example:

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Routes

Common routes in the current app:

- `/`
- `/app`
- `/app/projects`
- `/app/projects/:id/brief`
- `/app/projects/:id/script`
- `/app/projects/:id/scenes`
- `/app/projects/:id/renders`
- `/app/projects/:id/exports`
- `/app/presets`
- `/app/templates`
- `/app/assets`
- `/app/billing`
- `/app/settings/brand`
- `/app/settings/team`
- `/app/settings/providers`
- `/app/settings/workers`
- `/admin/queue`
- `/admin/workspaces`
- `/admin/renders`

## Important Files

- [package.json](./package.json): frontend scripts and dependencies
- [src/lib/config.ts](./src/lib/config.ts): mock vs live API mode
- [src/app/router.tsx](./src/app/router.tsx): route definitions
- [src/lib/mock-api.ts](./src/lib/mock-api.ts): older mock layer
- [src/lib/mock-service.ts](./src/lib/mock-service.ts): newer mock layer

## Known Gaps

- Tailwind migration is still in progress, and some legacy styling remains.
- Frontend architecture is split across older route-heavy pages and newer feature/hooks-based pages.
- Full backend integration is not complete across every screen.
- There is currently no committed frontend test suite.

## Troubleshooting

### The frontend opens, but data is mock data

That usually means `VITE_API_MODE` is still `mock`. Set:

```env
VITE_API_MODE=live
VITE_API_URL=http://localhost:8000
```

### `npm run build` fails

This is expected right now. The current TypeScript build issues are documented in [../frontend-report.md](../frontend-report.md).

### Docker frontend is up, but some actions still do not hit the backend

The Docker stack sets live mode, but parts of the current UI still rely on mock services while frontend/backend integration is being completed.


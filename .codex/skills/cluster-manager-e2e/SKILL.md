---
name: cluster-manager-e2e
description: Run end-to-end checks for Aerospike Cluster Manager. Use when Codex needs to start the full stack in containers, run the faster host-based dev stack, execute Playwright specs, inspect screenshots or traces, or shut the environment down after frontend or API changes.
---

# Cluster Manager E2E

Use this skill whenever a change affects frontend behavior, backend API wiring, or compose-based local environments.

## Choose the Mode

- Use `container` mode for production-like end-to-end validation.
- Use `dev` mode for faster iteration with host-side backend/frontend hot reload.
- Use `explore` after the chosen mode is already running and you want manual browser inspection.

## Run Container Mode

1. Start the full stack:

```bash
podman compose -f compose.yaml down
podman compose -f compose.yaml up -d --build
```

2. Wait for readiness:

```bash
until curl -sf http://localhost:8000/api/health >/dev/null 2>&1; do sleep 3; done
until curl -sf http://localhost:3100 >/dev/null 2>&1; do sleep 3; done
```

3. Run Playwright:

```bash
cd frontend && npx playwright test
```

4. Run a single spec or test filter when the task is narrower:

```bash
cd frontend && npx playwright test e2e/specs/04-records.spec.ts
cd frontend && npx playwright test -g "should create a connection"
```

## Run Dev Mode

1. Start the dev infrastructure:

```bash
podman compose -f compose.dev.yaml down 2>/dev/null
podman compose -f compose.dev.yaml up -d
```

2. Run the backend on the host:

```bash
cd backend
AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790 \
uv run uvicorn aerospike_cluster_manager_api.main:app --reload --host 0.0.0.0 --port 8000
```

3. Run the frontend on the host:

```bash
cd frontend && npm run dev
```

4. Override the base URL when running Playwright against the host frontend:

```bash
cd frontend && BASE_URL=http://localhost:3000 npx playwright test
```

## Explore and Inspect

- Open `http://localhost:3100` in container mode or `http://localhost:3000` in dev mode.
- Prefer existing page objects and fixtures under `frontend/e2e/pages/` and `frontend/e2e/fixtures/` when debugging or extending coverage.
- Use `npx playwright show-report` for HTML results and `npx playwright show-trace <trace.zip>` when failures produce traces.

## Stop the Environment

Container mode:

```bash
podman compose -f compose.yaml down
```

Dev mode:

```bash
podman compose -f compose.dev.yaml down
```

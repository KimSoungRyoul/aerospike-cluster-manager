---
name: e2e-dev
description: Local dev E2E environment — Aerospike in container, Backend + Frontend running locally
disable-model-invocation: true
arguments:
  - name: action
    description: "start | test | explore | stop | all (default: all)"
    required: false
  - name: spec
    description: "Specific spec file or test name filter (optional, for test action)"
    required: false
---

# E2E Dev — Local Development E2E Testing

Local development E2E environment. Only Aerospike runs in containers — Backend and Frontend run locally. Hot-reload is enabled for fast feedback on code changes.

## Architecture

```
compose.dev.yaml (containers)
  ├── aerospike-node-1,2,3  (host port 14790, 14791, 14792)
  ├── aerospike-exporter-1,2,3 (Prometheus 9145-9147)
  └── aerospike-tools

Local processes
  ├── backend   (port 8000, uv run uvicorn --reload)
  └── frontend  (port 3000, npm run dev) ← Playwright targets here
```

### e2e-test vs e2e-dev Differences

| | e2e-test | e2e-dev |
|---|---|---|
| Compose file | `compose.yaml` | `compose.dev.yaml` |
| Aerospike ports | Private (internal network) | 14790, 14791, 14792 |
| Backend | Container | Local (`uv run uvicorn --reload`) |
| Frontend | Container (port 3100) | Local (`npm run dev`, port 3000) |
| E2E target URL | `localhost:3100` | `localhost:3000` |
| Hot-reload | None | Yes (Backend + Frontend) |
| Use case | CI/pre-deployment verification | Local development + fast feedback |

## Actions

### `all` (default) — Run full workflow

Executes start → test → stop in sequence.

### `start` — Start environment

**Step 1: Start Aerospike cluster**

```bash
podman compose -f compose.dev.yaml down 2>/dev/null
podman compose -f compose.dev.yaml up -d
```

Wait for Aerospike health check:
```bash
until podman compose -f compose.dev.yaml ps --format json | grep -q '"Health":"healthy"'; do sleep 3; done
```

**Step 2: Start Backend (separate terminal/background)**

```bash
cd backend && AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790 uv run uvicorn aerospike_cluster_manager_api.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for Backend health check:
```bash
until curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do sleep 2; done
```

**Step 3: Start Frontend (separate terminal/background)**

```bash
cd frontend && npm run dev
```

Verify Frontend is accessible:
```bash
until curl -sf http://localhost:3000 > /dev/null 2>&1; do sleep 2; done
```

**Environment variable notes**:
- Backend: `AEROSPIKE_HOST=localhost`, `AEROSPIKE_PORT=14790` (host-mapped port from compose.dev.yaml)
- Frontend `BACKEND_URL` defaults to `http://localhost:8000` (next.config.ts rewrites)

**Aerospike Tools usage**:
```bash
# Connect to aql
podman exec -it aerospike-tools aql -h aerospike-node-1

# Connect to asadm
podman exec -it aerospike-tools asadm -h aerospike-node-1
```

### `test` — Run Playwright specs

The environment must already be running. **Note**: The local dev server uses port 3000, so a `baseURL` override is required.

```bash
# Run all specs (override baseURL to localhost:3000)
cd frontend && BASE_URL=http://localhost:3000 npx playwright test

# Run specific spec
cd frontend && BASE_URL=http://localhost:3000 npx playwright test e2e/specs/{spec}

# Filter by name
cd frontend && BASE_URL=http://localhost:3000 npx playwright test -g "{test name}"
```

**Note**: `playwright.config.ts` has `baseURL` set to `http://localhost:3100`. In the local dev environment, Frontend runs on port 3000, so override it with the `BASE_URL` environment variable.

### `explore` — Manual browser exploration via playwright-cli

The environment must already be running. Use the `playwright-cli` skill to open a browser and manually explore the app.

```bash
playwright-cli open http://localhost:3000
playwright-cli snapshot
playwright-cli click e3
playwright-cli screenshot
playwright-cli close
```

This mode is useful for:
- Immediate visual verification after code changes (with hot-reload)
- Bug reproduction and debugging
- Exploring selectors before writing E2E specs

### `stop` — Stop environment

```bash
# Stop Aerospike containers
podman compose -f compose.dev.yaml down
```

Backend/Frontend are local processes — stop them with Ctrl+C or terminate the processes.

To also delete volume data:
```bash
podman compose -f compose.dev.yaml down -v
```

## Troubleshooting

- **Aerospike startup failure**: Check logs with `podman compose -f compose.dev.yaml logs -f`
- **Backend connection failure**: Verify `AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790` is set
- **Frontend API proxy failure**: Verify Backend is running on port 8000 — `curl http://localhost:8000/api/health`
- **Port conflicts**: Check if ports Aerospike(14790-14792), Backend(8000), Frontend(3000) are already in use
- **Frontend port 3000 vs 3100**: Local dev uses 3000 (`npm run dev`), container mode uses 3100 (`compose.yaml`)

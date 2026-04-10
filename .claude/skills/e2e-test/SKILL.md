---
name: e2e-test
description: Run full-stack E2E tests with podman compose + Playwright
disable-model-invocation: true
arguments:
  - name: action
    description: "start | test | explore | stop | all (default: all)"
    required: false
  - name: spec
    description: "Specific spec file or test name filter (optional, for test/explore action)"
    required: false
---

# E2E Test — Full-Stack End-to-End Testing (Container Mode)

A workflow for running E2E tests with the entire stack in containers. Uses `compose.yaml` to start Aerospike + Backend + Frontend all as containers, then runs Playwright tests against `localhost:3100`.

> **For E2E testing in a local development environment, use `/e2e-dev`.** e2e-dev runs only Aerospike in containers while Backend/Frontend run locally, enabling hot-reload.

## Architecture

```
compose.yaml (all containers — Aerospike ports private, internal network only)
  ├── aerospike-node-1,2,3  (internal only, no host ports)
  ├── aerospike-tools        (aql, asadm, etc.)
  ├── aerospike-exporter-1,2,3 (Prometheus 9145-9147)
  ├── backend               (port 8000, FastAPI)
  └── frontend              (port 3100, Next.js) ← Playwright targets here
```

**Aerospike Tools usage**:
```bash
podman exec -it aerospike-tools aql -h aerospike-node-1
podman exec -it aerospike-tools asadm -h aerospike-node-1
```

## Actions

### `all` (default) — Run full workflow

Executes start → test → stop in sequence.

### `start` — Start infrastructure

1. Clean up existing containers and build/start the full stack:
```bash
podman compose -f compose.yaml down && podman compose -f compose.yaml up -d --build
```

2. Verify service readiness (health check):
```bash
# Backend health check (wait up to 120 seconds)
until curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do sleep 3; done

# Verify Frontend is accessible
until curl -sf http://localhost:3100 > /dev/null 2>&1; do sleep 3; done
```

3. Check overall container status:
```bash
podman compose -f compose.yaml ps
```

**Important**: Backend starts only after all 3 Aerospike nodes are healthy. Frontend starts only after Backend is healthy. Full startup may take 1-2 minutes.

### `test` — Run Playwright specs

Infrastructure must already be running.

```bash
# Run all specs
cd frontend && npx playwright test

# Run specific spec
cd frontend && npx playwright test e2e/specs/{spec}

# Filter by name
cd frontend && npx playwright test -g "{test name}"
```

**Playwright project structure**:
- `setup` project: runs `01-connection.spec.ts` (creates test data)
- `features` project: runs remaining specs (depends on `setup`)

**Available spec files**:
| Spec | Description |
|------|------|
| `01-connection.spec.ts` | Connection management (setup project) |
| `02-cluster.spec.ts` | Cluster information |
| `03-browser.spec.ts` | Namespace/set browser |
| `04-records.spec.ts` | Record CRUD |
| `05-query.spec.ts` | Query builder |
| `06-indexes.spec.ts` | Secondary indexes |
| `08-udfs.spec.ts` | UDF management |
| `09-terminal.spec.ts` | AQL terminal |
| `10-settings.spec.ts` | Settings |
| `11-navigation.spec.ts` | Navigation |

**Viewing test results**:
```bash
# Open HTML report
cd frontend && npx playwright show-report

# View trace on failure
cd frontend && npx playwright show-trace e2e/test-results/{trace-path}/trace.zip
```

### `explore` — Manual browser exploration via playwright-cli

Infrastructure must already be running. Use the `playwright-cli` skill to open a browser and manually explore the app.

```bash
# Open browser
playwright-cli open http://localhost:3100

# Check current state with snapshot
playwright-cli snapshot

# Interact with elements — click, fill, etc.
playwright-cli click e3
playwright-cli fill e5 "test-value"

# Take screenshot
playwright-cli screenshot

# Close browser
playwright-cli close
```

This mode is useful for:
- Visual verification after implementing new features
- Bug reproduction and debugging
- Exploring selectors before writing E2E specs

### `stop` — Stop infrastructure

```bash
podman compose -f compose.yaml down
```

To also delete volume data:
```bash
podman compose -f compose.yaml down -v
```

## Global Setup/Teardown

Playwright has its own global setup/teardown:
- **global-setup** (`e2e/global-setup.ts`): Waits up to 120 seconds for Frontend (`localhost:3100`) and Backend API (`localhost:3100/api/health`) to become accessible
- **global-teardown** (`e2e/global-teardown.ts`): Automatically cleans up test connections with the `E2E` prefix

## Configuration

| Setting | Value |
|------|-----|
| Base URL | `http://localhost:3100` |
| Test timeout | 60s |
| Expect timeout | 15s |
| Action timeout | 10s |
| Navigation timeout | 30s |
| Workers | 1 (sequential execution) |
| Screenshots | Always captured |
| Traces | Retained on failure |
| Output | `frontend/e2e/test-results/` |
| Screenshots | `frontend/e2e/screenshots/` |

## Troubleshooting

- **Containers won't start**: Check logs with `podman compose -f compose.yaml logs -f`
- **Backend health check failure**: Verify all Aerospike nodes are healthy — `podman compose -f compose.yaml ps`
- **Frontend inaccessible**: Backend must be healthy first — `curl http://localhost:8000/api/health`
- **Debugging after test failure**: Use Playwright Inspector — `cd frontend && npx playwright test --debug e2e/specs/{spec}`
- **Port conflicts**: See `.env.example` to change `BACKEND_PORT`, `FRONTEND_PORT`

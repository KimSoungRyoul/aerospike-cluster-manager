---
name: cluster-manager-local-setup
description: Verify that a local machine is ready for Aerospike Cluster Manager development. Use when Codex needs to check container runtime support, Node.js and Python toolchains, uv, Playwright browsers, backend/frontend dependencies, or the commands required to boot the repo for the first time.
---

# Cluster Manager Local Setup

Use this skill before a first local run or when an environment issue blocks the normal dev workflow.

## Check Tooling

- Container runtime:

```bash
docker --version 2>/dev/null || podman --version 2>/dev/null
docker compose version 2>/dev/null || podman compose --version 2>/dev/null
```

- Node.js and npm:

```bash
node --version
npm --version
```

- Python and uv:

```bash
python3 --version
uv --version
```

Target versions are Node 22 and Python 3.13.

## Install Project Dependencies

Frontend:

```bash
cd frontend && npm ci
cd frontend && npx playwright install
```

Backend:

```bash
cd backend && uv sync
```

## Verify the Repo Boots

Use one of these startup paths:

- Full container stack:

```bash
podman compose -f compose.yaml up -d --build
```

- Host dev stack:

```bash
podman compose -f compose.dev.yaml up -d
cd backend && AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790 uv run uvicorn aerospike_cluster_manager_api.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## Report Readiness Clearly

Summarize the environment as a short checklist: runtime, Node, Python, uv, frontend deps, backend deps, Playwright, and whether either startup path works.

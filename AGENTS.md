# Aerospike Cluster Manager

This repo is a full-stack Aerospike management UI with a FastAPI backend, a Next.js frontend, and Podman Compose-based local environments.

## Repo Map

- `backend/src/aerospike_cluster_manager_api/`: FastAPI app, routers, Pydantic models, and Kubernetes integration.
- `backend/tests/`: backend tests.
- `frontend/src/`: Next.js App Router code, shared API client, Zustand stores, and UI components.
- `frontend/e2e/`: Playwright specs, fixtures, and page objects.
- `compose.yaml`: full containerized stack for end-to-end testing.
- `compose.dev.yaml`: local-dev stack with Aerospike and Postgres in containers, backend/frontend on the host.

## Local Skills

- `.codex/skills/cluster-manager-e2e`: Start the right stack and run Playwright tests.
- `.codex/skills/cluster-manager-api-sync`: Keep backend models and frontend types aligned.
- `.codex/skills/cluster-manager-local-setup`: Verify local tools and dependencies.

## Working Rules

- Treat backend and frontend as separate toolchains with separate validation commands.
- Keep backend Pydantic models and frontend API types synchronized whenever request or response payloads change.
- Preserve React 19 and Next.js 16 patterns already used in the repo; avoid introducing alternate state or routing styles without need.
- Prefer `podman compose` commands already documented in the repo for full-stack verification.
- When touching Kubernetes-management features, verify both the backend endpoints and frontend consumers.

## Validation

- Backend install: `cd backend && uv sync`
- Backend lint: `cd backend && uv run ruff check src/`
- Backend format check: `cd backend && uv run ruff format --check src/`
- Backend tests: `cd backend && uv run pytest tests/ -v --tb=short`
- Frontend install: `cd frontend && npm ci`
- Frontend type check: `cd frontend && npm run type-check`
- Frontend lint: `cd frontend && npm run lint`
- Frontend format check: `cd frontend && npm run format:check`
- Frontend unit tests: `cd frontend && npm run test`
- Frontend build: `cd frontend && npm run build`
- E2E: use the `cluster-manager-e2e` skill to choose dev-mode or container-mode execution.

## Contract Invariants

- `backend/src/.../models/` and `frontend/src/lib/api/types.ts` must stay aligned.
- Frontend request helpers should keep matching backend route shapes and error semantics.
- Playwright assumes numbered specs and page-object helpers under `frontend/e2e/pages/`.
- Dev-mode E2E uses `localhost:3000`; container-mode E2E uses `localhost:3100`.

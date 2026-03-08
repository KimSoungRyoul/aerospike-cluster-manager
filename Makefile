# Makefile — Task runner for Aerospike Cluster Manager
# Usage: make <target>

.PHONY: dev dev-up dev-down up down test test-backend test-frontend \
        lint lint-backend lint-frontend type-check build pre-commit clean

# ---------------------------------------------------------------------------
# Podman Compose — development (Aerospike only)
# ---------------------------------------------------------------------------

dev: dev-up
	@echo ""
	@echo "Aerospike dev cluster is running."
	@echo "Start the backend:   cd backend  && AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790 uv run uvicorn aerospike_cluster_manager_api.main:app --reload"
	@echo "Start the frontend:  cd frontend && npm run dev"

dev-up:
	podman compose -f compose.dev.yaml up -d

dev-down:
	podman compose -f compose.dev.yaml down

# ---------------------------------------------------------------------------
# Podman Compose — full stack
# ---------------------------------------------------------------------------

up:
	podman compose -f compose.yaml up --build

down:
	podman compose -f compose.yaml down

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest tests/ -v --tb=short

test-frontend:
	cd frontend && npm run test

# ---------------------------------------------------------------------------
# Linting & formatting
# ---------------------------------------------------------------------------

lint: lint-backend lint-frontend

lint-backend:
	cd backend && uv run ruff check src --fix && uv run ruff format src

lint-frontend:
	cd frontend && npm run lint:fix && npm run format

# ---------------------------------------------------------------------------
# Type checking & build
# ---------------------------------------------------------------------------

type-check:
	cd frontend && npm run type-check

build:
	cd frontend && npm run build

# ---------------------------------------------------------------------------
# Pre-commit & cleanup
# ---------------------------------------------------------------------------

pre-commit:
	pre-commit run --all-files

clean:
	podman compose -f compose.yaml down 2>/dev/null || true
	podman compose -f compose.dev.yaml down 2>/dev/null || true

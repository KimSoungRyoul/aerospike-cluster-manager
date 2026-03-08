---
name: cluster-manager-api-sync
description: Synchronize backend Pydantic models with frontend API types in Aerospike Cluster Manager. Use when Codex changes request or response models, adds or removes fields, adjusts enum values, or reviews type mismatches between FastAPI routes and TypeScript consumers.
---

# Cluster Manager API Sync

Use this skill when backend model changes could drift from `frontend/src/lib/api/types.ts`.

## Source of Truth

- Backend models live in `backend/src/aerospike_cluster_manager_api/models/`.
- Frontend shared types live in `frontend/src/lib/api/types.ts`.
- Router behavior lives in `backend/src/aerospike_cluster_manager_api/routers/`.
- Frontend consumers usually live under `frontend/src/lib/api/`, stores, and route-specific components.

## Sync Workflow

1. Read the changed backend model file or domain.
2. Compare it with the matching frontend type block.
3. Update missing, extra, or mismatched fields in `types.ts`.
4. Check the router return shape if any field is computed or renamed.
5. Update frontend callers if the contract changed in a breaking way.

## Type Mapping

| Backend | Frontend |
| --- | --- |
| `str` | `string` |
| `int`, `float` | `number` |
| `bool` | `boolean` |
| `list[T]` | `T[]` |
| `dict[str, T]` | `Record<string, T>` |
| `Optional[T]` or `T | None` | `T | undefined` or optional property |
| `Literal[...]` | string literal union |
| `datetime` | `string` |

## Conventions

- Keep PascalCase type names aligned with backend model names.
- Avoid `any`; use exact unions or `unknown` when the shape is genuinely open.
- Preserve the existing grouping and ordering in `types.ts` when possible.
- Call out ambiguous mappings instead of silently narrowing semantics.

## Validate

```bash
cd backend && uv run pytest tests/ -v --tb=short
cd frontend && npm run type-check
```

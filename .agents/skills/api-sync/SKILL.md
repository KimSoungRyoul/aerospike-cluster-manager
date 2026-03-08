---
name: api-sync
description: Sync backend Pydantic models with frontend TypeScript types
disable-model-invocation: true
arguments:
  - name: model
    description: "Specific model domain to sync (e.g., connection, cluster, record). If omitted, syncs all."
    required: false
---

# API Type Sync

Synchronize backend Pydantic models with frontend TypeScript type definitions.

## Source Files

- **Backend models**: `backend/src/aerospike_cluster_manager_api/models/`
  - `connection.py`, `cluster.py`, `record.py`, `index.py`, `admin.py`, `metrics.py`, `query.py`, `terminal.py`, `udf.py`
- **Frontend types**: `frontend/src/lib/api/types.ts`

## Workflow

1. **Read backend models** from the specified domain (or all if not specified)
2. **Read frontend types** from `types.ts`
3. **Compare and identify differences**:
   - Missing types in frontend
   - Missing/extra fields
   - Type mismatches (e.g., `Optional[str]` vs `string | undefined`)
   - Naming inconsistencies
4. **Update `types.ts`** to match the backend models
5. **Run type-check** to verify: `cd frontend && npm run type-check`

## Type Mapping Reference

| Python (Pydantic)         | TypeScript                      |
|---------------------------|---------------------------------|
| `str`                     | `string`                        |
| `int`, `float`            | `number`                        |
| `bool`                    | `boolean`                       |
| `list[T]`                 | `T[]`                           |
| `dict[str, T]`            | `Record<string, T>`             |
| `Optional[T]`             | `T \| undefined` or `T?` field  |
| `T \| None = None`        | `T?` (optional field)           |
| `Literal["a", "b"]`       | `"a" \| "b"`                    |
| `datetime`                | `string` (ISO format)           |
| `Enum`                    | `string` literal union or enum  |

## Conventions

- Frontend interfaces use PascalCase matching Python class names
- Request types use `{Name}Request` suffix
- Response types use `{Name}Response` suffix when distinct from model
- Preserve existing field ordering in `types.ts`
- Keep grouped by domain (connection, cluster, record, etc.)
- Do NOT add `any` types — use specific types or `unknown`

## Output

After syncing, report:
- Fields added/removed/changed
- Any ambiguous mappings that need manual review

# execute_info_read_only — read-only asinfo verb whitelist

**Date**: 2026-05-07
**Branch**: `feature/mcp-execute-info-readonly-whitelist`
**Follows up**: PR #302 (MCP Phase 1) review Major M2

## Problem

PR #302 placed both `execute_info` and `execute_info_on_node` into `WRITE_TOOLS` because asinfo can issue writes (`set-config:`, `recluster:`, `truncate-namespace:`, etc.). Under `ACM_MCP_ACCESS_PROFILE=read_only` this leaves no path for safe diagnostic reads (`namespaces`, `version`, `roster:`, `racks:`, `xdr-dc:`, `latencies`, `statistics`). LLMs can fall back to `list_namespaces` / `get_nodes` for the most common reads, but lose every less-common diagnostic verb.

## Decision

Add a third info tool `execute_info_read_only` (mutation=False) gated by an **explicit closed allowlist** of safe verbs. The existing two mutation tools are unchanged.

| Tool | Profile | Verb scope |
|---|---|---|
| `execute_info` | FULL only | any |
| `execute_info_on_node` | FULL only | any |
| `execute_info_read_only` (NEW) | READ_ONLY + FULL | whitelist only |

## Tool surface

```python
@tool(category="info", mutation=False)
async def execute_info_read_only(
    conn_id: str,
    command: str,
    node_name: str | None = None,
) -> dict[str, Any]:
    """Run a safe diagnostic asinfo verb under any access profile.

    Verb is checked against READ_ONLY_INFO_VERBS. Unknown / write verbs
    return code=invalid_argument.

    node_name=None  -> info_random_node(command)
    node_name="X"   -> info_all then filter to X
    """
```

## Whitelist (25 verbs)

```python
READ_ONLY_INFO_VERBS: frozenset[str] = frozenset({
    # Cluster meta (8)
    "version", "build", "build-os", "build-time",
    "node", "service", "services", "services-alumni",
    # Cluster topology / health (7)
    "nodes", "cluster-name", "cluster-stable",
    "cluster-generation", "cluster-info",
    "health-outliers", "health-stats",
    # Namespace / set / index (5)
    "namespaces", "namespace",
    "sets", "bins", "sindex",
    # Stats (3)
    "statistics", "latencies", "udf-list",
    # Strong-consistency / rack / XDR (4)
    "roster", "racks", "xdr-dc", "dc",
})
```

### Excluded with rationale

| Verb / family | Why excluded |
|---|---|
| `dump-fabric:`, `dump-msgs:`, `dump-namespace:` | Server-side log/file output side-effects. Phase 2.1 follow-up — needs server-impact audit. |
| `latency:` (legacy) | Deprecated in CE 8.1. Use `latencies`. |
| `quiesces`, `quiesce-undo` | Mutation. |
| `set-config:`, `truncate-namespace:`, `recluster:`, `set-roster:`, `create-roster:`, `sindex-create:`, `sindex-delete:` | Mutation. |
| `eviction` | Read but rarely useful, conservative cut. Add when a real use case appears. |

## Verb parsing

```python
def extract_verb(command: str) -> str:
    cmd = command.strip()
    if not cmd:
        raise InfoVerbNotAllowed("")
    return cmd.split(":", 1)[0].split("/", 1)[0]
```

- Splits on first `:` (e.g., `roster:namespace=test` → `roster`).
- Then splits on first `/` (e.g., `sets/test/myset` → `sets`).
- Whitespace trimmed.
- Empty / whitespace-only → rejected.
- Case-sensitive (asinfo is case-sensitive).

## Error code

`code="invalid_argument"`, NOT `access_denied`. Reason: `access_denied` implies a policy block where the LLM should escalate; here the LLM should pick a different verb. `invalid_argument` is the correct retry signal.

Error message includes a hint: `"Verb {verb!r} not in read-only whitelist; pick from: {first 5 verbs}, ... or use execute_info under FULL access."`

## File map

| File | Change |
|---|---|
| `api/src/aerospike_cluster_manager_api/info_verbs.py` | NEW — `READ_ONLY_INFO_VERBS`, `InfoVerbNotAllowed`, `extract_verb`, `assert_read_only`. Top-level (matches `pk.py`/`predicate.py`) so the service layer can import without crossing the `mcp/` boundary. |
| `api/src/aerospike_cluster_manager_api/services/clusters_service.py` | Add `execute_info_read_only(conn_id, command, node_name)`. |
| `api/src/aerospike_cluster_manager_api/mcp/tools/info_commands.py` | Add `execute_info_read_only` tool wrapper. Update `execute_info` / `execute_info_on_node` docstrings to point at the new tool. |
| `api/src/aerospike_cluster_manager_api/mcp/errors.py` | Map `InfoVerbNotAllowed` → `MCPToolError(code="invalid_argument")`. |
| `api/tests/test_info_verbs.py` | NEW — domain unit tests. |
| `api/tests/test_clusters_service.py` | Service-layer tests for `execute_info_read_only`. |
| `api/tests/mcp/test_info_tools.py` | MCP tool tests (allow + block paths). |
| `api/tests/mcp/test_e2e_readonly.py` | Add positive case under READ_ONLY. |
| `api/tests/mcp/test_errors.py` | Mapping unit test. |
| `api/tests/mcp/conftest.py` | `EXPECTED_TOOL_COUNT = 21` → `22`. |

## Out of scope (Phase 2.1+)

- `dump-*` debug verbs (need server-impact audit).
- `eviction` and other lesser-used reads (add as use cases surface).
- Per-Aerospike-version whitelist (CE 8.1 only for now).
- Streaming `info_all` mode (current spec is single-node).

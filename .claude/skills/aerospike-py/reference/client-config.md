# Client Config Reference

## Table of Contents
- [ClientConfig](#clientconfig)
- [Connection Patterns](#connection-patterns)
- [Performance Tuning](#performance-tuning)

---

## ClientConfig

Import from `aerospike_py.types`. Used by `aerospike.client(config)` and `AsyncClient(config)`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| hosts | list[tuple[str, int]] | **required** | Seed host addresses |
| cluster_name | str | None | Expected cluster name |
| auth_mode | int | AUTH_INTERNAL (0) | Authentication mode |
| user | str | None | Username for authentication |
| password | str | None | Password for authentication |
| timeout | int | 30000 | Connection timeout (ms) |
| idle_timeout | int | 55000 | Idle connection timeout (ms) |
| max_conns_per_node | int | 300 | Max connections per node |
| min_conns_per_node | int | 0 | Min connections per node (pre-warm) |
| conn_pools_per_node | int | 1 | Connection pools per node |
| tend_interval | int | 1000 | Cluster tend interval (ms) |
| use_services_alternate | bool | false | Use alternate service addresses |

### Basic Example

```python
import aerospike_py as aerospike
from aerospike_py.types import ClientConfig

config: ClientConfig = {
    "hosts": [("127.0.0.1", 3000)],
    "cluster_name": "docker",
}
client = aerospike.client(config).connect()
```

### Multi-Node Cluster

The client discovers all nodes from any reachable seed:

```python
config: ClientConfig = {
    "hosts": [
        ("node1.example.com", 3000),
        ("node2.example.com", 3000),
        ("node3.example.com", 3000),
    ],
}
```

### Authentication

```python
# Internal auth
client = aerospike.client({
    "hosts": [("127.0.0.1", 3000)],
    "auth_mode": aerospike.AUTH_INTERNAL,
}).connect("admin", "admin")

# External (LDAP) auth
client = aerospike.client({
    "hosts": [("127.0.0.1", 3000)],
    "auth_mode": aerospike.AUTH_EXTERNAL,
}).connect("ldap_user", "ldap_pass")
```

---

## Connection Patterns

### Sync Client

```python
# Context manager (recommended)
with aerospike.client(config).connect() as client:
    record = client.get(key)
# close() called automatically

# Manual lifecycle
client = aerospike.client(config).connect()
try:
    record = client.get(key)
finally:
    client.close()
```

### Async Client

```python
# Context manager (recommended)
async with aerospike.AsyncClient(config) as client:
    await client.connect()
    record = await client.get(key)

# Manual lifecycle
client = aerospike.AsyncClient(config)
await client.connect()
try:
    record = await client.get(key)
finally:
    await client.close()
```

**Use async for:** High-concurrency web servers, fan-out reads, mixed I/O.
**Sync is fine for:** Scripts, batch jobs, sequential pipelines.

---

## Performance Tuning

### Connection Pool Sizing

```python
config: ClientConfig = {
    "hosts": [("127.0.0.1", 3000)],
    "max_conns_per_node": 300,
    "min_conns_per_node": 10,
    "conn_pools_per_node": 1,
    "idle_timeout": 55000,
}
```

- **max_conns_per_node**: Match to expected concurrent requests per node.
- **min_conns_per_node**: Set > 0 to avoid cold-start latency spikes.
- **conn_pools_per_node**: Machines with 8 or fewer CPU cores need only 1. On machines with more cores, increasing this value reduces lock contention on pooled connections.
- **idle_timeout**: Keep below server `proto-fd-idle-ms` (default 60s).

### Timeout Configuration

| Setting | Recommendation |
|---------|---------------|
| `socket_timeout` | 1-5s. Catches hung connections. |
| `total_timeout` | Set based on SLA. Includes retries. |
| `max_retries` | 2-3 for reads, 0 for writes (idempotency). |

### Batch Size Recommendations

- Use `batch_read()` instead of sequential `get()` calls -- single round-trip vs N round-trips.
- Use `select()` or `batch_read(keys, bins=[...])` to read only needed bins, reducing network I/O.
- For numeric workloads, use `batch_read()` with `_dtype` parameter for NumPy structured array output.

### Expression Filters vs Secondary Indexes

Push filtering to the server to reduce network transfer:

```python
from aerospike_py import exp

# Server-side filtering (preferred -- less network transfer)
expr = exp.eq(exp.bool_bin("active"), exp.bool_val(True))
results = client.query("test", "demo").results(
    policy={"filter_expression": expr}
)
```

The policy key for expression filters is always `"filter_expression"`.

### Tokio Runtime Workers

aerospike-py uses an internal Tokio async runtime with 2 worker threads by default. This is sufficient for most I/O-bound database operations.

```bash
# Override if you need more parallelism for heavy batch operations
export AEROSPIKE_RUNTIME_WORKERS=4
```

| Workers | Use Case |
|---------|----------|
| 2 (default) | Most applications, ML serving, web servers |
| 4 | Heavy batch operations, high-throughput pipelines |
| 8+ | Rarely needed; profile first |

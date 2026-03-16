# Types Reference

## Table of Contents
- [Return Types (NamedTuple)](#return-types)
- [Policy Types (TypedDict)](#policy-types)
- [Internal Types](#internal-types)

---

## Return Types

All read operations return NamedTuple instances with named field access and tuple unpacking.
Import from `aerospike_py.types`.

### Record
`(key: AerospikeKey | None, meta: RecordMetadata | None, bins: dict[str, Any] | None)`

Returned by `get`, `select`, `operate`, `batch_operate`, `batch_remove`, `Query.results`.

| Field | Type | Description |
|-------|------|-------------|
| key | AerospikeKey \| None | Record key |
| meta | RecordMetadata \| None | Generation and TTL |
| bins | dict[str, Any] \| None | Bin values |

```python
record = client.get(key)
print(record.bins)         # attribute access
_, meta, bins = record     # tuple unpacking
```

### AerospikeKey
`(namespace: str, set_name: str, user_key: str | int | bytes | None, digest: bytes)`

| Field | Type | Description |
|-------|------|-------------|
| namespace | str | Namespace |
| set_name | str | Set name |
| user_key | str \| int \| bytes \| None | Primary key (`None` unless written with `POLICY_KEY_SEND`) |
| digest | bytes | 20-byte RIPEMD-160 digest |

### RecordMetadata
`(gen: int, ttl: int)`

| Field | Type | Description |
|-------|------|-------------|
| gen | int | Record generation (write count, used for optimistic locking) |
| ttl | int | Seconds until expiration |

### ExistsResult
`(key: AerospikeKey | None, meta: RecordMetadata | None)`

Returned by `exists`. `meta` is `None` if the record does not exist.

| Field | Type | Description |
|-------|------|-------------|
| key | AerospikeKey \| None | Record key |
| meta | RecordMetadata \| None | `None` if record does not exist |

### OperateOrderedResult
`(key: AerospikeKey | None, meta: RecordMetadata | None, ordered_bins: list[BinTuple])`

Returned by `operate_ordered`. Preserves operation order in results.

| Field | Type | Description |
|-------|------|-------------|
| key | AerospikeKey \| None | Record key |
| meta | RecordMetadata \| None | Record metadata |
| ordered_bins | list[BinTuple] | Ordered operation results |

### BinTuple
`(name: str, value: Any)`

Single bin name-value pair used in `OperateOrderedResult.ordered_bins`.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Bin name |
| value | Any | Bin value |

### InfoNodeResult
`(node_name: str, error_code: int, response: str)`

Returned by `info_all`. One result per cluster node.

| Field | Type | Description |
|-------|------|-------------|
| node_name | str | Cluster node name |
| error_code | int | 0 on success |
| response | str | Info response string |

### Return Type Quick Reference

| Method | Return Type |
|--------|-------------|
| `get()`, `select()` | `Record` |
| `exists()` | `ExistsResult` |
| `operate()` | `Record` |
| `operate_ordered()` | `OperateOrderedResult` |
| `info_all()` | `list[InfoNodeResult]` |
| `batch_read()` | `BatchRecords` \| `NumpyBatchRecords` |
| `batch_operate()`, `batch_remove()` | `list[Record]` |
| `Query.results()` | `list[Record]` |

---

## Policy Types

All fields are optional (`total=False`) unless noted. Import from `aerospike_py.types`.

### ReadPolicy

Used by: `get()`, `select()`, `exists()`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| socket_timeout | int | 30000 | Socket timeout (ms) |
| total_timeout | int | 1000 | Total transaction timeout (ms) |
| max_retries | int | 2 | Max retry attempts |
| sleep_between_retries | int | 0 | Sleep between retries (ms) |
| filter_expression | Any | | Expression filter |
| replica | int | POLICY_REPLICA_SEQUENCE | Replica policy (`POLICY_REPLICA_*`) |
| read_mode_ap | int | POLICY_READ_MODE_AP_ONE | AP read mode (`POLICY_READ_MODE_AP_*`) |

### WritePolicy

Used by: `put()`, `remove()`, `touch()`, `append()`, `prepend()`, `increment()`, `remove_bin()`, `operate()`, `operate_ordered()`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| socket_timeout | int | 30000 | Socket timeout (ms) |
| total_timeout | int | 1000 | Total transaction timeout (ms) |
| max_retries | int | 0 | Max retry attempts |
| durable_delete | bool | false | Durable delete (Enterprise) |
| key | int | POLICY_KEY_DIGEST | Key send policy (`POLICY_KEY_*`) |
| exists | int | POLICY_EXISTS_IGNORE | Record exists policy (`POLICY_EXISTS_*`) |
| gen | int | POLICY_GEN_IGNORE | Generation policy (`POLICY_GEN_*`) |
| commit_level | int | POLICY_COMMIT_LEVEL_ALL | Commit level (`POLICY_COMMIT_LEVEL_*`) |
| ttl | int | 0 | Record TTL in seconds |
| filter_expression | Any | | Expression filter |

### WriteMeta

Used by: `put()`, `remove()`, `touch()`, `operate()` etc. as `meta` parameter

| Field | Type | Description |
|-------|------|-------------|
| gen | int | Expected generation for CAS (`POLICY_GEN_EQ`) |
| ttl | int | Record TTL in seconds |

### BatchPolicy

Used by: `batch_read()`, `batch_operate()`, `batch_remove()`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| socket_timeout | int | 30000 | Socket timeout (ms) |
| total_timeout | int | 1000 | Total transaction timeout (ms) |
| max_retries | int | 2 | Max retry attempts |
| filter_expression | Any | | Expression filter |

### QueryPolicy

Used by: `Query.results()`, `Query.foreach()`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| socket_timeout | int | 30000 | Socket timeout (ms) |
| total_timeout | int | 0 | Total timeout (0 = no limit) |
| max_retries | int | 2 | Max retry attempts |
| max_records | int | 0 | Max records to return (0 = all) |
| records_per_second | int | 0 | Rate limit (0 = unlimited) |
| filter_expression | Any | | Expression filter |

### AdminPolicy

Used by: all `admin_*` methods, index operations, `truncate()`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| timeout | int | 1000 | Admin operation timeout (ms) |

### Privilege

Used by: `admin_create_role()`, `admin_grant_privileges()`, `admin_revoke_privileges()`

| Field | Type | Description |
|-------|------|-------------|
| code | int | Privilege code (`PRIV_*`) |
| ns | str | Namespace scope (empty = global) |
| set | str | Set scope (empty = namespace-wide) |

### UserInfo (all required)

Returned by: `admin_query_user_info()`, `admin_query_users_info()`

| Field | Type | Description |
|-------|------|-------------|
| user | str | Username |
| roles | list[str] | Assigned role names |
| conns_in_use | int | Active connection count |

### RoleInfo (all required)

Returned by: `admin_query_role()`, `admin_query_roles()`

| Field | Type | Description |
|-------|------|-------------|
| name | str | Role name |
| privileges | list[Privilege] | Granted privileges |
| allowlist | list[str] | Allowed IP addresses |
| read_quota | int | Read quota |
| write_quota | int | Write quota |

---

## Internal Types

Import from `aerospike_py._types`.

### Operation

`dict[str, Any]` -- Operation dict for `client.operate()` / `client.operate_ordered()`.

Required keys:
- `op` (int): Operation code -- `OPERATOR_READ`, `OPERATOR_WRITE`, `OPERATOR_INCR`, `OPERATOR_APPEND`, `OPERATOR_PREPEND`, `OPERATOR_TOUCH`, `OPERATOR_DELETE`, or CDT codes (1000+).
- `bin` (str): Bin name to operate on.
- `val` (Any): Value for write operations; `None` for read ops.

Optional keys (CDT operations):
- `return_type` (int): `LIST_RETURN_*` or `MAP_RETURN_*` constant.
- `list_policy` (ListPolicy): Policy for list CDT operations.
- `map_policy` (MapPolicy): Policy for map CDT operations.
- `hll_policy` (HLLPolicy): Policy for HyperLogLog CDT operations.
- `bit_policy` (int): Bit write flags for bitwise CDT operations (`BIT_WRITE_*`).

Built by helper modules: `list_operations`, `map_operations`, `hll_operations`, `bit_operations`.

### ListPolicy

| Field | Type | Description |
|-------|------|-------------|
| order | int | `LIST_UNORDERED` or `LIST_ORDERED` |
| flags | int | `LIST_WRITE_*` flags |

### MapPolicy

| Field | Type | Description |
|-------|------|-------------|
| order | int | `MAP_UNORDERED`, `MAP_KEY_ORDERED`, `MAP_KEY_VALUE_ORDERED` |
| write_mode | int | `MAP_UPDATE`, `MAP_UPDATE_ONLY`, `MAP_CREATE_ONLY` |

### HLLPolicy

| Field | Type | Description |
|-------|------|-------------|
| flags | int | `HLL_WRITE_*` flags |

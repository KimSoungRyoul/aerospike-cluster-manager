---
name: aerospike-py
description: "aerospike-py Python client library (Rust/PyO3) - sync/async API for Aerospike NoSQL. CRUD, batch, CDT, query, expressions, NumPy, operate, admin, observability, FastAPI integration, error handling, and all types/constants."
user-invocable: false
---

Canonical type reference: `src/aerospike_py/__init__.pyi`

## 1. Client Setup

```python
import aerospike_py
from aerospike_py import AsyncClient

# Sync - method chaining
client = aerospike_py.client({"hosts": [("127.0.0.1", 18710)]}).connect()

# Sync - context manager
with aerospike_py.client(config).connect() as client:
    record = client.get(("test", "demo", "key1"))

# Sync - with auth
client = aerospike_py.client(config).connect("admin", "admin")

# Async - context manager
async with AsyncClient(config) as client:
    await client.connect()
    record = await client.get(("test", "demo", "key1"))
```

### ClientConfig

```python
config: dict = {
    "hosts": [("127.0.0.1", 18710)],  # required
    "cluster_name": "docker",
    "auth_mode": aerospike_py.AUTH_INTERNAL,  # AUTH_EXTERNAL=1, AUTH_PKI=2
    "user": "admin", "password": "admin",
    "timeout": 30000,              # connection timeout (ms)
    "idle_timeout": 55000,         # idle connection timeout (ms)
    "max_conns_per_node": 300, "min_conns_per_node": 0,
    "tend_interval": 1000,         # cluster health check interval (ms)
    "use_services_alternate": False,
}
```

### Connection Methods

```python
client.connect(username=None, password=None) -> Client  # returns self for chaining
client.is_connected() -> bool
client.close() -> None
client.get_node_names() -> list[str]
# Async: await connect(), await close(), await get_node_names()
```

Detail: `reference/client-config.md`

## 2. Return Types

All return types are NamedTuples (from `aerospike_py.types`):

```python
from aerospike_py.types import Record, AerospikeKey, RecordMetadata, \
    ExistsResult, OperateOrderedResult, BinTuple, InfoNodeResult

Record(key: AerospikeKey | None, meta: RecordMetadata | None, bins: dict[str, Any] | None)
AerospikeKey(namespace: str, set_name: str, user_key: str | int | bytes | None, digest: bytes)
RecordMetadata(gen: int, ttl: int)
ExistsResult(key: AerospikeKey | None, meta: RecordMetadata | None)
OperateOrderedResult(key: AerospikeKey | None, meta: RecordMetadata | None, ordered_bins: list[BinTuple])
BinTuple(name: str, value: Any)
InfoNodeResult(node_name: str, error_code: int, response: str)

# Field access and tuple unpacking
record = client.get(key)
record.bins["name"], record.meta.gen, record.meta.ttl
_, meta, bins = client.get(key)
```

## 3. CRUD

```python
key: tuple[str, str, str | int | bytes] = ("test", "demo", "user1")

# Write
client.put(key, {"name": "Alice", "age": 30})
client.put(key, {"score": 100}, meta={"ttl": 300})
client.put(key, {"x": 1}, policy={"exists": aerospike_py.POLICY_EXISTS_CREATE_ONLY})
client.put(key, {"x": 1}, meta={"gen": 2}, policy={"gen": aerospike_py.POLICY_GEN_EQ})

# Read -> Record
record = client.get(key)
record.bins   # {"name": "Alice", "age": 30}

# Select specific bins -> Record
record = client.select(key, ["name"])  # record.bins = {"name": "Alice"}

# Exists -> ExistsResult (meta is None if not found)
result = client.exists(key)
if result.meta is not None:
    print(f"Found, gen={result.meta.gen}")

# Delete
client.remove(key)
client.remove(key, meta={"gen": 3}, policy={"gen": aerospike_py.POLICY_GEN_EQ})

# Touch (reset TTL)
client.touch(key, val=300)

# String operations
client.append(key, "name", "_suffix")
client.prepend(key, "name", "prefix_")

# Numeric operations
client.increment(key, "counter", 1)
client.increment(key, "score", 0.5)   # float increment
client.increment(key, "counter", -1)  # decrement

# Remove specific bins
client.remove_bin(key, ["temp_bin", "debug_bin"])
```

> Async: add `await` to all I/O methods. `record = await client.get(key)`

## 4. Error Handling

```python
try:
    record = client.get(key)
except aerospike_py.RecordNotFound:
    print("Not found")
except aerospike_py.AerospikeTimeoutError:
    print("Timeout")
except aerospike_py.AerospikeError as e:
    print(f"Error: {e}")
```

Detail: `reference/admin.md`

Exception hierarchy:

```
AerospikeError
+-- ClientError, ClusterError, InvalidArgError, AerospikeTimeoutError
+-- RecordError
|   +-- RecordNotFound, RecordExistsError, RecordGenerationError, RecordTooBig
|   +-- BinNameError, BinExistsError, BinNotFound, BinTypeError, FilteredOut
+-- ServerError
    +-- AerospikeIndexError (IndexNotFound, IndexFoundError)
    +-- QueryError (QueryAbortedError)
    +-- AdminError, UDFError
```

## 5. Batch Operations

```python
keys = [("test", "demo", f"user_{i}") for i in range(10)]

# batch_read -> BatchRecords
batch = client.batch_read(keys)
for br in batch.batch_records:
    if br.result == 0 and br.record is not None:
        key_tuple, meta_dict, bins = br.record
        print(bins)

# Read specific bins
batch = client.batch_read(keys, bins=["name", "age"])

# batch_operate -> list[Record]
ops = [{"op": aerospike_py.OPERATOR_INCR, "bin": "views", "val": 1}]
results: list[Record] = client.batch_operate(keys, ops)

# batch_remove -> list[Record]
results: list[Record] = client.batch_remove(keys)
```

### NumPy Batch

```python
import numpy as np

dtype = np.dtype([("age", "i4"), ("score", "f8"), ("name", "S32")])
result = client.batch_read(keys, bins=["age", "score", "name"], _dtype=dtype)

result.batch_records   # np.ndarray (structured array)
result.meta            # np.ndarray, dtype=[("gen", "u4"), ("ttl", "u4")]
result.result_codes    # np.ndarray (int32), 0 = success

row = result.get("user_0")  # lookup by primary key
ages = result.batch_records["age"]
mean_age = ages[result.result_codes == 0].mean()
```

## 6. Operate / Operate Ordered

Atomic multi-operation on a single record.

```python
# Operation dict format: {"op": OPERATOR_*, "bin": "name", "val": value}
ops = [
    {"op": aerospike_py.OPERATOR_INCR, "bin": "counter", "val": 1},
    {"op": aerospike_py.OPERATOR_READ, "bin": "counter", "val": None},
]
record: Record = client.operate(key, ops)
# Operators: READ=1, WRITE=2, INCR=5, APPEND=9, PREPEND=10, TOUCH=11, DELETE=12
```

### Ordered Results

```python
from aerospike_py.types import OperateOrderedResult, BinTuple

result: OperateOrderedResult = client.operate_ordered(key, ops)
for bt in result.ordered_bins:
    print(f"{bt.name} = {bt.value}")
```

CDT operations can be mixed into operate(). See Section 7.

## 7. CDT Operations

```python
from aerospike_py import list_operations as lop, map_operations as mop
```

### List CDT

```python
record = client.operate(key, [
    lop.list_append("mylist", "val"),
    lop.list_get("mylist", 0),
    lop.list_size("mylist"),
])
# Functions: list_append, list_append_items, list_insert, list_insert_items,
#   list_get, list_get_range, list_get_by_value, list_get_by_index,
#   list_get_by_rank, list_pop, list_pop_range, list_remove, list_remove_range,
#   list_set, list_trim, list_clear, list_increment, list_sort, list_size
```

### Map CDT

```python
record = client.operate(key, [
    mop.map_put("mymap", "k1", "v1"),
    mop.map_get_by_key("mymap", "k1", aerospike_py.MAP_RETURN_VALUE),
    mop.map_size("mymap"),
])
# Functions: map_put, map_put_items, map_increment, map_decrement,
#   map_get_by_key, map_get_by_key_range, map_get_by_value, map_get_by_index,
#   map_get_by_rank, map_remove_by_key, map_remove_by_value, map_clear, map_size
```

### CDT Constants

```python
# List: LIST_RETURN_NONE=0, LIST_RETURN_INDEX=1, LIST_RETURN_RANK=3,
#        LIST_RETURN_COUNT=5, LIST_RETURN_VALUE=7
#        LIST_UNORDERED, LIST_ORDERED, LIST_WRITE_DEFAULT, LIST_WRITE_ADD_UNIQUE

# Map: MAP_RETURN_NONE=0, MAP_RETURN_INDEX=1, MAP_RETURN_RANK=3,
#       MAP_RETURN_COUNT=5, MAP_RETURN_KEY=6, MAP_RETURN_VALUE=7,
#       MAP_RETURN_KEY_VALUE=8, MAP_RETURN_EXISTS=13
#       MAP_UNORDERED, MAP_KEY_ORDERED, MAP_KEY_VALUE_ORDERED
#       MAP_WRITE_FLAGS_DEFAULT, MAP_WRITE_FLAGS_CREATE_ONLY, MAP_WRITE_FLAGS_UPDATE_ONLY
```

Full function list: `reference/write.md`

## 8. Query & Index

```python
from aerospike_py import predicates as p

# Create secondary index
client.index_integer_create("test", "demo", "age", "age_idx")
client.index_string_create("test", "demo", "name", "name_idx")
client.index_remove("test", "age_idx")

# Build and execute query
query = client.query("test", "demo")
query.select("name", "age")
query.where(p.between("age", 20, 40))
records: list[Record] = query.results()

# foreach with callback (return False to stop early)
def process(record: Record) -> bool | None:
    print(record.bins)
    return None  # continue
query.foreach(process)

# Async
query = client.query("test", "demo")
query.where(p.equals("status", "active"))
records = await query.results()
```

### Predicates

```python
p.equals(bin_name, val)                  # exact match
p.between(bin_name, min_val, max_val)    # range (inclusive)
p.contains(bin_name, index_type, val)    # collection contains
# Geo predicates: not supported
```

## 9. Expression Filters

Server-side filtering (Aerospike 5.2+). No secondary index required.

```python
from aerospike_py import exp

# Comparison
expr = exp.gt(exp.int_bin("age"), exp.int_val(21))
record = client.get(key, policy={"filter_expression": expr})

# Compound (AND/OR)
expr = exp.and_(
    exp.gt(exp.int_bin("age"), exp.int_val(18)),
    exp.eq(exp.string_bin("status"), exp.string_val("active")),
)

# Metadata and bin existence
expr = exp.gt(exp.ttl(), exp.int_val(3600))  # TTL > 1 hour
expr = exp.bin_exists("optional_field")

# Regex
expr = exp.regex_compare(r"^user_", 0, exp.string_bin("name"))

# Variable binding
expr = exp.let_(
    exp.def_("x", exp.int_bin("a")),
    exp.gt(exp.var("x"), exp.int_val(10)),
)

# Apply in policies (key is always "filter_expression")
record = client.get(key, policy={"filter_expression": expr})
batch = client.batch_read(keys, policy={"filter_expression": expr})
query.results(policy={"filter_expression": expr})
```

### Expression Builder Functions

| Category | Functions |
|----------|-----------|
| Value | `int_val`, `float_val`, `string_val`, `bool_val`, `blob_val`, `list_val`, `map_val`, `geo_val`, `nil`, `infinity`, `wildcard` |
| Bin | `int_bin`, `float_bin`, `string_bin`, `bool_bin`, `blob_bin`, `list_bin`, `map_bin`, `geo_bin`, `hll_bin`, `bin_exists`, `bin_type` |
| Compare | `eq`, `ne`, `gt`, `ge`, `lt`, `le` |
| Logic | `and_`, `or_`, `not_`, `xor_` |
| Meta | `key`, `key_exists`, `set_name`, `record_size`, `last_update`, `since_update`, `void_time`, `ttl`, `is_tombstone`, `digest_modulo` |
| Numeric | `num_add`, `num_sub`, `num_mul`, `num_div`, `num_mod`, `num_pow`, `num_log`, `num_abs`, `num_floor`, `num_ceil`, `to_int`, `to_float`, `min_`, `max_` |
| Pattern | `regex_compare`, `geo_compare` |
| Control | `cond`, `var`, `def_`, `let_` |

Full reference: `reference/read.md`

## 10. Admin & Infrastructure

```python
# User management
client.admin_create_user("user1", "pass", ["read-write"])
client.admin_drop_user("user1")
client.admin_change_password("user1", "new_pass")
client.admin_grant_roles("user1", ["sys-admin"])
client.admin_revoke_roles("user1", ["read-write"])
client.admin_query_user_info("user1")  # -> dict (user, roles, conns_in_use)
client.admin_query_users_info()        # -> list[dict]

# Role management
client.admin_create_role("role1", [{"code": aerospike_py.PRIV_READ, "ns": "test", "set": ""}])
client.admin_drop_role("role1")
client.admin_grant_privileges("role1", [{"code": aerospike_py.PRIV_WRITE, "ns": "", "set": ""}])
client.admin_revoke_privileges("role1", [{"code": aerospike_py.PRIV_WRITE, "ns": "", "set": ""}])
# Privileges: PRIV_READ, PRIV_WRITE, PRIV_READ_WRITE, PRIV_READ_WRITE_UDF,
#   PRIV_SYS_ADMIN, PRIV_USER_ADMIN, PRIV_DATA_ADMIN, PRIV_UDF_ADMIN,
#   PRIV_SINDEX_ADMIN, PRIV_TRUNCATE

# UDF (Lua only)
client.udf_put("my_udf.lua")
result = client.apply(key, "my_udf", "my_function", [1, "hello"])
client.udf_remove("my_udf")

# Info
from aerospike_py.types import InfoNodeResult
results: list[InfoNodeResult] = client.info_all("namespaces")
for node_name, error_code, response in results:
    print(f"{node_name}: {response}")
response: str = client.info_random_node("build")

# Truncate
client.truncate("test", "demo")
client.truncate("test", "demo", nanos=1234567890)
```

## 11. Observability

```python
# Prometheus Metrics
aerospike_py.start_metrics_server(port=9464)  # /metrics HTTP endpoint
metrics_text: str = aerospike_py.get_metrics()  # Prometheus text format
aerospike_py.stop_metrics_server()

# OpenTelemetry Tracing (reads OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME env vars)
aerospike_py.init_tracing()
aerospike_py.shutdown_tracing()  # call before process exit

# Logging
aerospike_py.set_log_level(aerospike_py.LOG_LEVEL_DEBUG)
# LOG_LEVEL_OFF=-1, LOG_LEVEL_ERROR=0, LOG_LEVEL_WARN=1,
# LOG_LEVEL_INFO=2, LOG_LEVEL_DEBUG=3, LOG_LEVEL_TRACE=4
```

Detail: `reference/observability.md`

## 12. FastAPI Integration

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
import aerospike_py
from aerospike_py import AsyncClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    aerospike_py.set_log_level(aerospike_py.LOG_LEVEL_INFO)
    aerospike_py.init_tracing()
    client = AsyncClient({
        "hosts": [(os.getenv("AEROSPIKE_HOST", "127.0.0.1"), 18710)],
    })
    await client.connect()
    app.state.aerospike = client
    yield
    await client.close()
    aerospike_py.shutdown_tracing()

app = FastAPI(lifespan=lifespan)

def get_client(request: Request) -> AsyncClient:
    return request.app.state.aerospike

@app.put("/records/{pk}")
async def put_record(pk: str, data: dict, client: AsyncClient = Depends(get_client)):
    await client.put(("test", "demo", pk), data)
    return {"status": "ok"}

@app.get("/records/{pk}")
async def get_record(pk: str, client: AsyncClient = Depends(get_client)):
    try:
        record = await client.get(("test", "demo", pk))
        return record.bins
    except aerospike_py.RecordNotFound:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "not found"})
```

Detail: `reference/client-config.md` | `reference/types.md` | `reference/constants.md`

## 13. Policy Reference

```python
# ReadPolicy
{"socket_timeout": 30000, "total_timeout": 1000, "max_retries": 2,
 "filter_expression": expr, "replica": POLICY_REPLICA_MASTER, "read_mode_ap": POLICY_READ_MODE_AP_ONE}

# WritePolicy
{"socket_timeout": 30000, "total_timeout": 1000, "max_retries": 0,
 "durable_delete": False, "key": POLICY_KEY_DIGEST, "exists": POLICY_EXISTS_IGNORE,
 "gen": POLICY_GEN_IGNORE, "commit_level": POLICY_COMMIT_LEVEL_ALL,
 "ttl": 0, "filter_expression": expr}

# WriteMeta              BatchPolicy
{"gen": 1, "ttl": 300}  {"socket_timeout": 30000, "total_timeout": 1000,
                          "max_retries": 2, "filter_expression": expr}
# QueryPolicy            AdminPolicy
{"socket_timeout": 30000, "total_timeout": 0, "max_retries": 2,
 "max_records": 1000, "records_per_second": 0, "filter_expression": expr}
{"timeout": 5000}
```

### Key Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `POLICY_EXISTS_IGNORE` | 0 | Upsert (default) |
| `POLICY_EXISTS_CREATE_ONLY` | 4 | Error if exists |
| `POLICY_EXISTS_UPDATE_ONLY` | 1 | Error if not exists |
| `POLICY_EXISTS_REPLACE` | 2 | Full replace (drops other bins) |
| `POLICY_GEN_IGNORE` | 0 | Ignore generation (default) |
| `POLICY_GEN_EQ` | 1 | Write only if gen matches |
| `POLICY_GEN_GT` | 2 | Write only if gen is greater |
| `POLICY_KEY_DIGEST` | 0 | Store digest only (default) |
| `POLICY_KEY_SEND` | 1 | Store original key on server |
| `TTL_NAMESPACE_DEFAULT` | 0 | Use namespace default |
| `TTL_NEVER_EXPIRE` | -1 | Never expire |
| `TTL_DONT_UPDATE` | -2 | Keep existing TTL |

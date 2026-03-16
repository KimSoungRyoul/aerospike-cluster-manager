# Write Reference

## Table of Contents
- [Write Operations](#write-operations)
- [Operate / Operate Ordered](#operate--operate-ordered)
- [CDT Operations](#cdt-operations)
- [NumPy Batch Write](#numpy-batch-write)

---

## Write Operations

### put(key, bins, meta=None, policy=None)

Create or update a record.

```python
import aerospike_py as aerospike

key = ("test", "demo", "user1")

# Simple write
client.put(key, {"name": "Alice", "age": 30})

# Supported types: str, int, float, bytes, list, dict, bool, None
client.put(key, {
    "str_bin": "hello",
    "int_bin": 42,
    "float_bin": 3.14,
    "list_bin": [1, 2, 3],
    "map_bin": {"nested": "dict"},
})

# With TTL (seconds)
client.put(key, {"val": 1}, meta={"ttl": 300})

# Create only (fail if exists)
client.put(key, {"val": 1}, policy={"exists": aerospike.POLICY_EXISTS_CREATE_ONLY})

# Optimistic locking (generation check)
client.put(key, {"val": 2}, meta={"gen": 1}, policy={"gen": aerospike.POLICY_GEN_EQ})

# Async
await async_client.put(key, {"name": "Alice", "age": 30})
```

### remove(key, meta=None, policy=None)

Delete a record.

```python
client.remove(key)

# With generation check
client.remove(key, meta={"gen": 5}, policy={"gen": aerospike.POLICY_GEN_EQ})
```

### touch(key, val=0, meta=None, policy=None)

Reset record TTL without modifying bins.

```python
client.touch(key, val=600)  # reset TTL to 600 seconds
```

### append(key, bin, val, meta=None, policy=None)

Append string to a string bin.

```python
client.append(key, "name", " Smith")
```

### prepend(key, bin, val, meta=None, policy=None)

Prepend string to a string bin.

```python
client.prepend(key, "greeting", "Hello, ")
```

### increment(key, bin, offset, meta=None, policy=None)

Increment numeric bin value.

```python
client.increment(key, "age", 1)
client.increment(key, "score", 0.5)  # float increment
```

### remove_bin(key, bin_names, meta=None, policy=None)

Remove specific bins from a record.

```python
client.remove_bin(key, ["temp_bin", "debug_bin"])
```

### batch_operate(keys, ops, policy=None) -> list[Record]

Execute operations on multiple records in a single network call.

```python
ops = [{"op": aerospike.OPERATOR_INCR, "bin": "views", "val": 1}]
results: list[Record] = client.batch_operate(keys, ops)
```

### batch_remove(keys, policy=None) -> list[Record]

Delete multiple records in a single network call.

```python
results = client.batch_remove(keys)
```

### Optimistic Locking

```python
from aerospike_py.exception import RecordGenerationError

record = client.get(key)
try:
    client.put(
        key,
        {"val": record.bins["val"] + 1},
        meta={"gen": record.meta.gen},
        policy={"gen": aerospike.POLICY_GEN_EQ},
    )
except RecordGenerationError:
    print("Concurrent modification, retry needed")
```

### WritePolicy

| Key | Type | Description |
|-----|------|-------------|
| `socket_timeout` | int | Socket idle timeout (ms) |
| `total_timeout` | int | Total transaction timeout (ms) |
| `max_retries` | int | Maximum retry attempts |
| `durable_delete` | bool | Durable delete (requires Enterprise) |
| `key` | int | Key send policy |
| `exists` | int | Record existence policy |
| `gen` | int | Generation policy |
| `commit_level` | int | Commit level |
| `ttl` | int | Record TTL (seconds) |
| `filter_expression` | Expr | Expression filter |

### WriteMeta

| Key | Type | Description |
|-----|------|-------------|
| `gen` | int | Expected generation for CAS |
| `ttl` | int | Record TTL (seconds) |

---

## Operate / Operate Ordered

Execute multiple operations atomically on a single record.

### Operation Dict Format

```python
{"op": <OPERATOR_CONSTANT>, "bin": "<bin_name>", "val": <value>}
```

### Operator Constants

| Constant | Description |
|----------|-------------|
| `OPERATOR_READ` | Read a bin |
| `OPERATOR_WRITE` | Write a bin |
| `OPERATOR_INCR` | Increment a numeric bin |
| `OPERATOR_APPEND` | Append to a string bin |
| `OPERATOR_PREPEND` | Prepend to a string bin |
| `OPERATOR_TOUCH` | Touch record (reset TTL) |
| `OPERATOR_DELETE` | Delete record |

### operate(key, ops, meta=None, policy=None) -> Record

Returns a Record with bins from READ operations.

```python
ops = [
    {"op": aerospike.OPERATOR_WRITE, "bin": "name", "val": "Bob"},
    {"op": aerospike.OPERATOR_INCR, "bin": "counter", "val": 1},
    {"op": aerospike.OPERATOR_READ, "bin": "counter", "val": None},
]
record = client.operate(key, ops)
print(record.bins["counter"])

# Async
record = await async_client.operate(key, ops)
```

### operate_ordered(key, ops, meta=None, policy=None) -> OperateOrderedResult

Returns results in operation order.

```python
result = client.operate_ordered(key, ops)
for bt in result.ordered_bins:
    print(f"{bt.name} = {bt.value}")
```

---

## CDT Operations

All CDT operations return `Operation` dicts (`dict[str, Any]`) for use with
`client.operate()`, `client.operate_ordered()`, or `client.batch_operate()`.

### List Operations

Import: `from aerospike_py import list_operations as lop`

#### Write

| Function | Signature | Description |
|----------|-----------|-------------|
| list_append | (bin, val, policy=None) | Append a value |
| list_append_items | (bin, values, policy=None) | Append multiple values |
| list_insert | (bin, index, val, policy=None) | Insert value at index |
| list_insert_items | (bin, index, values, policy=None) | Insert multiple values at index |
| list_set | (bin, index, val) | Set value at index |
| list_increment | (bin, index, val, policy=None) | Increment value at index |
| list_sort | (bin, sort_flags=0) | Sort the list |
| list_set_order | (bin, list_order=0) | Set list ordering |

#### Read

| Function | Signature | Description |
|----------|-----------|-------------|
| list_get | (bin, index) | Get item at index |
| list_get_range | (bin, index, count) | Get count items from index |
| list_get_by_value | (bin, val, return_type) | Get items matching value |
| list_get_by_index | (bin, index, return_type) | Get item by index with return type |
| list_get_by_index_range | (bin, index, return_type, count=None) | Get items by index range |
| list_get_by_rank | (bin, rank, return_type) | Get item by rank |
| list_get_by_rank_range | (bin, rank, return_type, count=None) | Get items by rank range |
| list_get_by_value_list | (bin, values, return_type) | Get items matching any value in list |
| list_get_by_value_range | (bin, begin, end, return_type) | Get items with values in [begin, end) |

#### Remove

| Function | Signature | Description |
|----------|-----------|-------------|
| list_pop | (bin, index) | Remove and return item at index |
| list_pop_range | (bin, index, count) | Remove and return count items from index |
| list_remove | (bin, index) | Remove item at index |
| list_remove_range | (bin, index, count) | Remove count items from index |
| list_remove_by_value | (bin, val, return_type) | Remove items matching value |
| list_remove_by_value_list | (bin, values, return_type) | Remove items matching any value in list |
| list_remove_by_value_range | (bin, begin, end, return_type) | Remove items with values in [begin, end) |
| list_remove_by_index | (bin, index, return_type) | Remove item by index |
| list_remove_by_index_range | (bin, index, return_type, count=None) | Remove items by index range |
| list_remove_by_rank | (bin, rank, return_type) | Remove item by rank |
| list_remove_by_rank_range | (bin, rank, return_type, count=None) | Remove items by rank range |

#### Modify

| Function | Signature | Description |
|----------|-----------|-------------|
| list_trim | (bin, index, count) | Remove items outside [index, index+count) |
| list_clear | (bin) | Remove all items |

#### Info

| Function | Signature | Description |
|----------|-----------|-------------|
| list_size | (bin) | Return item count |

#### List Constants

| Constant | Value | Description |
|----------|-------|-------------|
| LIST_RETURN_NONE | 0 | No return |
| LIST_RETURN_INDEX | 1 | Return index |
| LIST_RETURN_REVERSE_INDEX | 2 | Return reverse index |
| LIST_RETURN_RANK | 3 | Return rank |
| LIST_RETURN_REVERSE_RANK | 4 | Return reverse rank |
| LIST_RETURN_COUNT | 5 | Return count |
| LIST_RETURN_VALUE | 7 | Return value |
| LIST_RETURN_EXISTS | 13 | Return existence boolean |
| LIST_UNORDERED | 0 | Unordered list |
| LIST_ORDERED | 1 | Ordered list |
| LIST_SORT_DEFAULT | 0 | Default sort |
| LIST_SORT_DROP_DUPLICATES | 2 | Drop duplicates on sort |
| LIST_WRITE_DEFAULT | 0 | Default write |
| LIST_WRITE_ADD_UNIQUE | 1 | Fail if value exists |
| LIST_WRITE_INSERT_BOUNDED | 2 | Enforce insert bounds |
| LIST_WRITE_NO_FAIL | 4 | No error on violation |
| LIST_WRITE_PARTIAL | 8 | Allow partial success |

#### ListPolicy

`TypedDict` with optional fields: `order` (int), `flags` (int).
Import from `aerospike_py._types`.

#### List Example

```python
from aerospike_py import list_operations as list_ops

# Atomic: sort, get top 3
ops = [
    list_ops.list_sort("scores"),
    list_ops.list_get_by_rank_range(
        "scores", -3, aerospike.LIST_RETURN_VALUE, count=3
    ),
]
_, _, bins = client.operate(key, ops)

# Remove scores below 80
ops = [
    list_ops.list_remove_by_value_range(
        "scores", 0, 80, aerospike.LIST_RETURN_COUNT
    ),
]
_, _, bins = client.operate(key, ops)
```

---

### Map Operations

Import: `from aerospike_py import map_operations as mop`

#### Write

| Function | Signature | Description |
|----------|-----------|-------------|
| map_put | (bin, key, val, policy=None) | Put a key/value pair |
| map_put_items | (bin, items, policy=None) | Put multiple key/value pairs |
| map_increment | (bin, key, incr, policy=None) | Increment value by key |
| map_decrement | (bin, key, decr, policy=None) | Decrement value by key |
| map_set_order | (bin, map_order) | Set map ordering |

#### Read

| Function | Signature | Description |
|----------|-----------|-------------|
| map_get_by_key | (bin, key, return_type) | Get item by key |
| map_get_by_key_range | (bin, begin, end, return_type) | Get items with keys in [begin, end) |
| map_get_by_key_list | (bin, keys, return_type) | Get items matching any key in list |
| map_get_by_value | (bin, val, return_type) | Get items by value |
| map_get_by_value_range | (bin, begin, end, return_type) | Get items with values in [begin, end) |
| map_get_by_value_list | (bin, values, return_type) | Get items matching any value in list |
| map_get_by_index | (bin, index, return_type) | Get item by index |
| map_get_by_index_range | (bin, index, return_type, count=None) | Get items by index range |
| map_get_by_rank | (bin, rank, return_type) | Get item by rank |
| map_get_by_rank_range | (bin, rank, return_type, count=None) | Get items by rank range |

#### Remove

| Function | Signature | Description |
|----------|-----------|-------------|
| map_remove_by_key | (bin, key, return_type) | Remove item by key |
| map_remove_by_key_list | (bin, keys, return_type) | Remove items by key list |
| map_remove_by_key_range | (bin, begin, end, return_type) | Remove items with keys in [begin, end) |
| map_remove_by_value | (bin, val, return_type) | Remove items by value |
| map_remove_by_value_list | (bin, values, return_type) | Remove items by value list |
| map_remove_by_value_range | (bin, begin, end, return_type) | Remove items with values in [begin, end) |
| map_remove_by_index | (bin, index, return_type) | Remove item by index |
| map_remove_by_index_range | (bin, index, return_type, count=None) | Remove items by index range |
| map_remove_by_rank | (bin, rank, return_type) | Remove item by rank |
| map_remove_by_rank_range | (bin, rank, return_type, count=None) | Remove items by rank range |

#### Info

| Function | Signature | Description |
|----------|-----------|-------------|
| map_clear | (bin) | Remove all items |
| map_size | (bin) | Return item count |

#### Map Constants

| Constant | Value | Description |
|----------|-------|-------------|
| MAP_RETURN_NONE | 0 | No return |
| MAP_RETURN_INDEX | 1 | Return index |
| MAP_RETURN_REVERSE_INDEX | 2 | Return reverse index |
| MAP_RETURN_RANK | 3 | Return rank |
| MAP_RETURN_REVERSE_RANK | 4 | Return reverse rank |
| MAP_RETURN_COUNT | 5 | Return count |
| MAP_RETURN_KEY | 6 | Return key |
| MAP_RETURN_VALUE | 7 | Return value |
| MAP_RETURN_KEY_VALUE | 8 | Return key-value pairs |
| MAP_RETURN_EXISTS | 13 | Return existence boolean |
| MAP_UNORDERED | 0 | Unordered map |
| MAP_KEY_ORDERED | 1 | Key-ordered map |
| MAP_KEY_VALUE_ORDERED | 3 | Key-value-ordered map |
| MAP_WRITE_FLAGS_DEFAULT | 0 | Default write |
| MAP_WRITE_FLAGS_CREATE_ONLY | 1 | Error if key exists |
| MAP_WRITE_FLAGS_UPDATE_ONLY | 2 | Error if key not exists |
| MAP_WRITE_FLAGS_NO_FAIL | 4 | No error on violation |
| MAP_WRITE_FLAGS_PARTIAL | 8 | Allow partial success |

#### MapPolicy

`TypedDict` with optional fields: `order` (int), `write_mode` (int).
Import from `aerospike_py._types`.

#### Map Example

```python
from aerospike_py import map_operations as map_ops

# Get top 2 scores by rank
ops = [
    map_ops.map_get_by_rank_range(
        "scores", -2, aerospike.MAP_RETURN_KEY_VALUE, count=2
    ),
]
_, _, bins = client.operate(key, ops)

# Add a new score and increment an existing one
ops = [
    map_ops.map_put("scores", "history", 90),
    map_ops.map_increment("scores", "math", 5),
    map_ops.map_size("scores"),
]
_, _, bins = client.operate(key, ops)
```

---

### HLL Operations

Import: `from aerospike_py import hll_operations as hll_ops`

#### Write

| Function | Signature | Description |
|----------|-----------|-------------|
| hll_init | (bin, index_bit_count, minhash_bit_count=None, *, policy=None) | Create or reset HLL bin |
| hll_add | (bin, values, index_bit_count=None, minhash_bit_count=None, *, policy=None) | Add values to HLL bin |
| hll_set_union | (bin, values, *, policy=None) | Set union of HLL objects into bin |
| hll_fold | (bin, index_bit_count) | Fold HLL to lower index_bit_count |

#### Read

| Function | Signature | Description |
|----------|-----------|-------------|
| hll_get_count | (bin) | Return estimated element count |
| hll_get_union | (bin, values) | Return union HLL object |
| hll_get_union_count | (bin, values) | Return estimated union count |
| hll_get_intersect_count | (bin, values) | Return estimated intersection count |
| hll_get_similarity | (bin, values) | Return estimated Jaccard similarity |
| hll_describe | (bin) | Return [index_bit_count, minhash_bit_count] |

#### HLL Constants

| Constant | Value | Description |
|----------|-------|-------------|
| HLL_WRITE_DEFAULT | 0 | Default write mode |
| HLL_WRITE_CREATE_ONLY | 1 | Error if bin exists |
| HLL_WRITE_UPDATE_ONLY | 2 | Error if bin not exists |
| HLL_WRITE_NO_FAIL | 4 | No error on violation |
| HLL_WRITE_ALLOW_FOLD | 8 | Allow fold on set-union |

#### HLLPolicy

`TypedDict` with optional field: `flags` (int).
Import from `aerospike_py._types`.

#### Notes
- `index_bit_count` range: 4-16.
- `minhash_bit_count` range: 0 (disabled) or 4-51.
- `hll_fold` only works when `minhash_bit_count` is 0.
- `values` parameters for union/intersect/similarity are lists of HLL bin values (bytes).

---

### Bit Operations

Import: `from aerospike_py import bit_operations as bit_ops`

#### Write (Modify)

| Function | Signature | Description |
|----------|-----------|-------------|
| bit_resize | (bin, byte_size, resize_flags=0, policy=None) | Resize bytes bin to byte_size |
| bit_insert | (bin, byte_offset, value, policy=None) | Insert bytes at byte_offset |
| bit_remove | (bin, byte_offset, byte_size, policy=None) | Remove byte_size bytes at offset |
| bit_set | (bin, bit_offset, bit_size, value, policy=None) | Set bits at offset to value |
| bit_or | (bin, bit_offset, bit_size, value, policy=None) | Bitwise OR at offset |
| bit_xor | (bin, bit_offset, bit_size, value, policy=None) | Bitwise XOR at offset |
| bit_and | (bin, bit_offset, bit_size, value, policy=None) | Bitwise AND at offset |
| bit_not | (bin, bit_offset, bit_size, policy=None) | Negate bits at offset |
| bit_lshift | (bin, bit_offset, bit_size, shift, policy=None) | Left-shift bits |
| bit_rshift | (bin, bit_offset, bit_size, shift, policy=None) | Right-shift bits |
| bit_add | (bin, bit_offset, bit_size, value, signed=False, action=0, policy=None) | Add integer at bit offset |
| bit_subtract | (bin, bit_offset, bit_size, value, signed=False, action=0, policy=None) | Subtract integer at bit offset |
| bit_set_int | (bin, bit_offset, bit_size, value, policy=None) | Set integer value at bit offset |

#### Read

| Function | Signature | Description |
|----------|-----------|-------------|
| bit_get | (bin, bit_offset, bit_size) | Get bits as bytes |
| bit_count | (bin, bit_offset, bit_size) | Count set bits (popcount) |
| bit_lscan | (bin, bit_offset, bit_size, value) | Find first matching bit (left-to-right) |
| bit_rscan | (bin, bit_offset, bit_size, value) | Find first matching bit (right-to-left) |
| bit_get_int | (bin, bit_offset, bit_size, signed=False) | Get integer from bits |

#### Bit Constants

| Constant | Value | Description |
|----------|-------|-------------|
| BIT_WRITE_DEFAULT | 0 | Default write mode |
| BIT_WRITE_CREATE_ONLY | 1 | Error if bin exists |
| BIT_WRITE_UPDATE_ONLY | 2 | Error if bin not exists |
| BIT_WRITE_NO_FAIL | 4 | No error on violation |
| BIT_WRITE_PARTIAL | 8 | Allow partial success |
| BIT_RESIZE_DEFAULT | 0 | Default resize |
| BIT_RESIZE_FROM_FRONT | 1 | Resize from front |
| BIT_RESIZE_GROW_ONLY | 2 | Only allow growing |
| BIT_RESIZE_SHRINK_ONLY | 4 | Only allow shrinking |
| BIT_OVERFLOW_FAIL | 0 | Fail on overflow |
| BIT_OVERFLOW_SATURATE | 2 | Saturate on overflow |
| BIT_OVERFLOW_WRAP | 4 | Wrap on overflow |

#### Notes
- The `policy` parameter for bit operations is an `int` (`BIT_WRITE_*` constant), not a TypedDict.
- `bit_add` / `bit_subtract`: `bit_size` must be <= 64. `signed` controls signed/unsigned. `action` controls overflow behavior.
- `value` for `bit_set`, `bit_or`, `bit_xor`, `bit_and` must be `bytes` or `bytearray`.
- `value` for `bit_lscan`, `bit_rscan` is `bool` (`True` for 1, `False` for 0).

---

## NumPy Batch Write

Write records from a numpy structured array. One designated field serves as the primary key.

Requires `numpy >= 2.0`. Install with: `pip install aerospike-py[numpy]`

### batch_write_numpy(data, namespace, set_name, _dtype, key_field="_key", policy=None) -> list[Record]

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | `np.ndarray` | required | Structured numpy array with record data |
| `namespace` | `str` | required | Target Aerospike namespace |
| `set_name` | `str` | required | Target set name |
| `_dtype` | `np.dtype` | required | Structured dtype describing the array layout |
| `key_field` | `str` | `"_key"` | Name of the dtype field to use as the record user key |
| `policy` | `dict \| None` | `None` | Optional BatchPolicy overrides |

Returns `list[Record]` -- a list of `Record` NamedTuples `(key, meta, bins)` with write results.

### How It Works

- The `key_field` (default `"_key"`) column is extracted as the user key for each record
- All fields **not** prefixed with `_` become Aerospike bins
- Fields prefixed with `_` (other than the key field) are ignored

### Define dtype for Write

```python
import numpy as np

dtype = np.dtype([
    ("_key", "i4"),      # primary key field (prefixed with _)
    ("score", "f8"),     # bin: float64
    ("count", "i4"),     # bin: int32
])
```

### Supported dtype Kinds

| NumPy Kind | Code | Example | Aerospike Value |
|------------|------|---------|-----------------|
| Signed int | `i` | `"i1"`, `"i2"`, `"i4"`, `"i8"` | `Int(i64)` |
| Unsigned int | `u` | `"u1"`, `"u2"`, `"u4"`, `"u8"` | `Int(i64)` |
| Float | `f` | `"f4"`, `"f8"` | `Float(f64)` |
| Fixed bytes | `S` | `"S8"`, `"S16"` | `Blob(bytes)` or `String` |
| Void bytes | `V` | `"V4"`, `"V16"` | `Blob(bytes)` |
| Sub-array | -- | `("f4", (128,))` | `Blob(bytes)` |

> Unicode strings (`U`) and Python objects (`O`) are not supported. Use `S` (fixed bytes) for string data.

### Basic Write

```python
import numpy as np
import aerospike_py as aerospike

client = aerospike.client({"hosts": [("127.0.0.1", 3000)]}).connect()

dtype = np.dtype([
    ("_key", "i4"),
    ("score", "f8"),
    ("count", "i4"),
])

data = np.array([
    (1, 0.95, 10),
    (2, 0.87, 20),
    (3, 0.72, 15),
], dtype=dtype)

results = client.batch_write_numpy(data, "test", "demo", dtype)

# Check results
for record in results:
    key, meta, bins = record
    print(f"Key: {key}, Gen: {meta.gen}")

# Async
results = await async_client.batch_write_numpy(data, "test", "demo", dtype)
```

### Custom Key Field

```python
dtype = np.dtype([("user_id", "i8"), ("score", "f8")])
data = np.array([(100, 1.5), (101, 2.5)], dtype=dtype)

# Use "user_id" as key instead of "_key"
results = client.batch_write_numpy(
    data, "test", "demo", dtype, key_field="user_id"
)
```

> When using a custom `key_field`, the field name should **not** start with `_` if you want it also stored as a bin.

### Pandas DataFrame to Aerospike

```python
import pandas as pd

df = pd.DataFrame({"user_id": [1, 2, 3], "score": [0.95, 0.87, 0.72], "level": [10, 20, 15]})

dtype = np.dtype([("_key", "i4"), ("score", "f8"), ("level", "i4")])
data = np.zeros(len(df), dtype=dtype)
data["_key"] = df["user_id"].values
data["score"] = df["score"].values
data["level"] = df["level"].values

results = client.batch_write_numpy(data, "test", "users", dtype)
```

### Write and Read Roundtrip

```python
# Write
write_dtype = np.dtype([("_key", "i4"), ("x", "f8"), ("y", "f8"), ("category", "i4")])
data = np.array([(1, 1.0, 2.0, 0), (2, 3.0, 4.0, 1), (3, 5.0, 6.0, 0)], dtype=write_dtype)
client.batch_write_numpy(data, "test", "points", write_dtype)

# Read back with _dtype
read_dtype = np.dtype([("x", "f8"), ("y", "f8"), ("category", "i4")])
keys = [("test", "points", i) for i in range(1, 4)]
batch = client.batch_read(keys, _dtype=read_dtype, policy={"key": aerospike.POLICY_KEY_SEND})

print(batch.batch_records["x"].mean())       # 3.0
print(batch.batch_records["category"].sum())  # 1
```

### Best Practices

- **Match dtype to data** -- use smallest sufficient dtype (`"f4"` vs `"f8"`, `"i2"` vs `"i8"`)
- **Batch size** -- keep arrays at 100-5,000 rows per call
- **Key field convention** -- use `"_key"` as the default key field
- **Underscore prefix** -- fields starting with `_` are excluded from bins
- **Large datasets** -- split into chunks:

```python
chunk_size = 1000
for i in range(0, len(data), chunk_size):
    chunk = data[i:i + chunk_size]
    client.batch_write_numpy(chunk, "test", "demo", dtype)
```

# Read Reference

## Table of Contents
- [Read Operations](#read-operations)
- [Query & Secondary Index](#query--secondary-index)
- [Expression Filters](#expression-filters)
- [NumPy Batch Read](#numpy-batch-read)

---

## Read Operations

### Keys

Every record is identified by a key tuple: `(namespace, set, primary_key)`.

```python
key = ("test", "demo", "user1")      # string PK
key = ("test", "demo", 12345)         # integer PK
key = ("test", "demo", b"\x01\x02")   # bytes PK
```

### get(key, policy=None) -> Record

Read all bins of a record.

```python
from aerospike_py import Record

record: Record = client.get(key)
print(record.bins)       # {"name": "Alice", "age": 30}
print(record.meta.gen)   # 1
print(record.meta.ttl)   # 2591998

# Tuple unpacking (backward compat)
_, meta, bins = client.get(key)

# Async
record = await async_client.get(key)
```

### select(key, bins, policy=None) -> Record

Read specific bins only.

```python
record = client.select(key, ["name"])
# record.bins = {"name": "Alice"}
```

### exists(key, policy=None) -> ExistsResult

Check record existence (returns metadata only, no bin data).

```python
from aerospike_py import ExistsResult

result: ExistsResult = client.exists(key)
if result.meta is not None:
    print(f"gen={result.meta.gen}")
```

### batch_read(keys, bins=None, policy=None, _dtype=None) -> BatchRecords | NumpyBatchRecords

Read multiple records in a single network call.

```python
keys = [("test", "demo", f"user_{i}") for i in range(10)]

# All bins
batch = client.batch_read(keys)
for br in batch.batch_records:
    if br.result == 0 and br.record is not None:
        print(br.record.bins)

# Specific bins
batch = client.batch_read(keys, bins=["name", "age"])

# Existence check only
batch = client.batch_read(keys, bins=[])

# Async
batch = await async_client.batch_read(keys, bins=["name", "age"])
```

### ReadPolicy

| Key | Type | Description |
|-----|------|-------------|
| `socket_timeout` | int | Socket idle timeout (ms) |
| `total_timeout` | int | Total transaction timeout (ms) |
| `max_retries` | int | Maximum retry attempts |
| `sleep_between_retries` | int | Sleep between retries (ms) |
| `filter_expression` | Expr | Expression filter |
| `replica` | int | Replica algorithm |
| `read_mode_ap` | int | Read mode for AP namespaces |

### Tips

- **Batch size**: 100-5,000 keys per batch is optimal. Very large batches may timeout.
- **Timeouts**: Increase `total_timeout` for large batch operations.
- **Error handling**: Individual batch records can fail independently. Always check `br.record` for `None`.

---

## Query & Secondary Index

### Index Management

| Function | Description |
|----------|-------------|
| `index_integer_create(ns, set, bin, name)` | Create integer secondary index |
| `index_string_create(ns, set, bin, name)` | Create string secondary index |
| `index_geo2dsphere_create(ns, set, bin, name)` | Create geospatial secondary index |
| `index_remove(ns, name)` | Remove secondary index |

```python
client.index_integer_create("test", "users", "age", "users_age_idx")
client.index_string_create("test", "users", "city", "users_city_idx")
client.index_remove("test", "users_age_idx")
```

### Query Builder

```python
from aerospike_py import predicates, Record

query = client.query("test", "users")
query.select("name", "age")           # select specific bins
query.where(predicates.between("age", 25, 35))  # set predicate

records: list[Record] = query.results()          # collect all results
query.foreach(callback)                           # iterate with callback
```

### Callback Iteration

```python
def process(record: Record) -> None:
    print(f"{record.bins['name']}: age {record.bins['age']}")

query.foreach(process)

# Return False to stop early
count = 0
def limited(record: Record):
    global count
    count += 1
    if count >= 5:
        return False  # stop iteration

query.foreach(limited)
```

### Predicates

Import: `from aerospike_py import predicates`

| Function | Description |
|----------|-------------|
| `equals(bin, val)` | Equality match |
| `between(bin, min, max)` | Range (inclusive) |
| `contains(bin, idx_type, val)` | List/map contains |
| `geo_within_geojson_region(bin, geojson)` | Points in region |
| `geo_within_radius(bin, lat, lng, radius)` | Points in circle (meters) |
| `geo_contains_geojson_point(bin, geojson)` | Regions containing point |

> **Note**: Geo predicates emit a `FutureWarning` and raise `ClientError` at execution time (not yet supported).

### Geospatial Query Examples

```python
# Points within a polygon
region = '{"type":"Polygon","coordinates":[[[126.9,37.5],[126.9,37.6],[127.0,37.6],[127.0,37.5],[126.9,37.5]]]}'
query.where(predicates.geo_within_geojson_region("location", region))

# Points within radius (meters)
query.where(predicates.geo_within_radius("location", 37.5665, 126.978, 5000.0))

# Regions containing a point
point = '{"type":"Point","coordinates":[126.978, 37.5665]}'
query.where(predicates.geo_contains_geojson_point("coverage", point))
```

---

## Expression Filters

Server-side filtering (Aerospike Server >= 5.2). No secondary index required.
Import: `from aerospike_py import exp`

All functions return `Expr` (dict with `__expr__` key). Pass to any read/write/batch/query policy:

```python
policy = {"filter_expression": expr}
```

### Value Constructors

| Function | Description |
|----------|-------------|
| `int_val(val)` | Integer constant (64-bit) |
| `float_val(val)` | Float constant (64-bit) |
| `string_val(val)` | String constant |
| `bool_val(val)` | Boolean constant |
| `blob_val(val)` | Bytes constant |
| `list_val(val)` | List constant |
| `map_val(val)` | Map/dict constant |
| `geo_val(val)` | GeoJSON string |
| `nil()` | Null value |
| `infinity()` | Infinity (range upper bound) |
| `wildcard()` | Wildcard (matches any) |

### Bin Accessors

| Function | Description |
|----------|-------------|
| `int_bin(name)` | Read integer bin |
| `float_bin(name)` | Read float bin |
| `string_bin(name)` | Read string bin |
| `bool_bin(name)` | Read boolean bin |
| `blob_bin(name)` | Read bytes bin |
| `list_bin(name)` | Read list bin |
| `map_bin(name)` | Read map bin |
| `geo_bin(name)` | Read geo bin |
| `hll_bin(name)` | Read HyperLogLog bin |
| `bin_exists(name)` | Check bin exists (returns bool expr) |
| `bin_type(name)` | Get bin particle type |

### Record Metadata

| Function | Description |
|----------|-------------|
| `key(exp_type)` | Record primary key (use `EXP_TYPE_*` constant) |
| `key_exists()` | Check if key was stored in record metadata |
| `set_name()` | Record set name |
| `record_size()` | Record size in bytes (server 7.0+) |
| `last_update()` | Last update time (nanoseconds since epoch) |
| `since_update()` | Time since last update (milliseconds) |
| `void_time()` | Record expiration time (nanoseconds since epoch) |
| `ttl()` | Record TTL in seconds |
| `is_tombstone()` | Check if tombstone record |
| `digest_modulo(modulo)` | Key digest mod N (for sampling) |

Type constants for `key(exp_type)`: `EXP_TYPE_NIL`(0), `EXP_TYPE_BOOL`(1), `EXP_TYPE_INT`(2), `EXP_TYPE_STRING`(3), `EXP_TYPE_LIST`(4), `EXP_TYPE_MAP`(5), `EXP_TYPE_BLOB`(6), `EXP_TYPE_FLOAT`(7), `EXP_TYPE_GEO`(8), `EXP_TYPE_HLL`(9).

### Comparison

All take `(left, right)` and return a boolean expression.

| Function | Operator |
|----------|----------|
| `eq(left, right)` | `==` |
| `ne(left, right)` | `!=` |
| `gt(left, right)` | `>` |
| `ge(left, right)` | `>=` |
| `lt(left, right)` | `<` |
| `le(left, right)` | `<=` |

### Logical

| Function | Description |
|----------|-------------|
| `and_(*exprs)` | Logical AND (variadic) |
| `or_(*exprs)` | Logical OR (variadic) |
| `not_(expr)` | Logical NOT |
| `xor_(*exprs)` | Logical XOR (variadic) |

### Numeric

| Function | Description |
|----------|-------------|
| `num_add(*exprs)` | Sum (variadic) |
| `num_sub(*exprs)` | Subtract (variadic) |
| `num_mul(*exprs)` | Multiply (variadic) |
| `num_div(*exprs)` | Divide (variadic) |
| `num_mod(numerator, denominator)` | Modulo |
| `num_pow(base, exponent)` | Power |
| `num_log(num, base)` | Logarithm |
| `num_abs(value)` | Absolute value |
| `num_floor(num)` | Floor |
| `num_ceil(num)` | Ceiling |
| `to_int(num)` | Convert to integer |
| `to_float(num)` | Convert to float |
| `min_(*exprs)` | Minimum (variadic) |
| `max_(*exprs)` | Maximum (variadic) |

### Integer Bitwise

| Function | Description |
|----------|-------------|
| `int_and(*exprs)` | Bitwise AND (variadic) |
| `int_or(*exprs)` | Bitwise OR (variadic) |
| `int_xor(*exprs)` | Bitwise XOR (variadic) |
| `int_not(expr)` | Bitwise NOT |
| `int_lshift(value, shift)` | Left shift |
| `int_rshift(value, shift)` | Logical right shift |
| `int_arshift(value, shift)` | Arithmetic right shift |
| `int_count(expr)` | Bit count (popcount) |
| `int_lscan(value, search)` | Scan from MSB for bit value |
| `int_rscan(value, search)` | Scan from LSB for bit value |

### Pattern Matching

| Function | Description |
|----------|-------------|
| `regex_compare(regex, flags, bin_expr)` | Regex match on string expression |
| `geo_compare(left, right)` | Geospatial contains/within comparison |

`regex_compare` flags: `0` = default, `1` = extended, `2` = icase, `4` = nosub, `8` = newline.

### Control Flow

| Function | Description |
|----------|-------------|
| `cond(*exprs)` | Conditional: `cond(bool1, val1, bool2, val2, ..., default)` |
| `var(name)` | Variable reference |
| `def_(name, value)` | Variable definition (used inside `let_`) |
| `let_(*exprs)` | Variable binding scope: `let_(def_("x", ...), ..., body_expr)` |

### Advanced Patterns

#### Basic Comparison and Logic

```python
from aerospike_py import exp

# age > 18 AND status == "active"
expr = exp.and_(
    exp.gt(exp.int_bin("age"), exp.int_val(18)),
    exp.eq(exp.string_bin("status"), exp.string_val("active")),
)
record = client.get(key, policy={"filter_expression": expr})
```

#### Variable Binding

```python
expr = exp.let_(
    exp.def_("total", exp.num_add(exp.int_bin("a"), exp.int_bin("b"))),
    exp.gt(exp.var("total"), exp.int_val(100)),
)
```

#### Conditional Branching

```python
expr = exp.cond(
    exp.gt(exp.int_bin("score"), exp.int_val(90)), exp.string_val("A"),
    exp.gt(exp.int_bin("score"), exp.int_val(80)), exp.string_val("B"),
    exp.string_val("C"),  # default
)
```

#### Regex and Geo

```python
expr = exp.regex_compare(r"^user_\d+$", 0, exp.string_bin("username"))

expr = exp.geo_compare(
    exp.geo_bin("location"),
    exp.geo_val('{"type":"AeroCircle","coordinates":[[-122.0,37.5],5000.0]}'),
)
```

#### Metadata Filters

```python
# Expiring within 1 hour
exp.lt(exp.ttl(), exp.int_val(3600))

# Sample ~10% of records
exp.eq(exp.digest_modulo(10), exp.int_val(0))

# Check if bit 3 is set in flags
exp.ne(
    exp.int_and(exp.int_bin("flags"), exp.int_val(0x08)),
    exp.int_val(0),
)
```

#### Policy Usage

Expressions work with any read/write/batch/query policy:

```python
expr = exp.and_(
    exp.ge(exp.int_bin("age"), exp.int_val(21)),
    exp.eq(exp.bool_bin("verified"), exp.bool_val(True)),
)

record = client.get(key, policy={"filter_expression": expr})
record = await async_client.get(key, policy={"filter_expression": expr})
results = client.batch_read(keys, policy={"filter_expression": expr})
records = query.results(policy={"filter_expression": expr})
```

#### Practical Examples

```python
# Active premium users
expr = exp.and_(
    exp.eq(exp.bool_bin("active"), exp.bool_val(True)),
    exp.or_(
        exp.eq(exp.string_bin("tier"), exp.string_val("gold")),
        exp.eq(exp.string_bin("tier"), exp.string_val("platinum")),
    ),
    exp.ge(exp.int_bin("age"), exp.int_val(18)),
)
records = client.query("test", "users").results(policy={"filter_expression": expr})

# Records expiring within 1 hour
expr = exp.and_(
    exp.gt(exp.ttl(), exp.int_val(0)),
    exp.lt(exp.ttl(), exp.int_val(3600)),
)

# High-value transactions
expr = exp.gt(
    exp.num_mul(exp.float_bin("amount"), exp.int_bin("quantity")),
    exp.float_val(10000.0),
)
```

---

## NumPy Batch Read

High-performance batch reads using NumPy structured arrays. Data flows directly between Aerospike and NumPy buffers via Rust, bypassing per-element Python object creation.

Requires `numpy >= 2.0`. Install with: `pip install aerospike-py[numpy]`

### When to Use

| Scenario | Regular `batch_read` | NumPy `batch_read` |
|----------|---------------------|-------------------|
| Records < 100 | Preferred | Overhead not justified |
| Records 100-10K | OK | **2-5x faster** |
| Records > 10K | Slow (dict allocation) | **5-10x faster** |
| Non-numeric bins | Required | Not supported |
| Vectorized analytics | Manual conversion | **Native numpy arrays** |

### Define a dtype

Each field in the dtype maps to an Aerospike bin name:

```python
import numpy as np

dtype = np.dtype([
    ("score", "f8"),     # float64
    ("count", "i4"),     # int32
    ("level", "u2"),     # uint16
    ("tag", "S8"),       # 8-byte fixed string
])
```

### Supported dtype Kinds

| NumPy kind | Code | Examples | Aerospike type |
|-----------|------|---------|---------------|
| Signed int | `i` | `i1`, `i2`, `i4`, `i8` | Integer |
| Unsigned int | `u` | `u1`, `u2`, `u4`, `u8` | Integer |
| Float | `f` | `f2`, `f4`, `f8` | Float |
| Fixed bytes | `S` | `S8`, `S16`, `S32` | String (truncated) |
| Void bytes | `V` | `V8`, `V16` | Blob (truncated) |

> Variable-length strings (`U`), objects (`O`), and datetime (`M`/`m`) are **not supported**.

### Read into NumPy Arrays

```python
keys = [("test", "demo", f"user_{i}") for i in range(1000)]

result = client.batch_read(keys, bins=["score", "count", "level", "tag"], _dtype=dtype)
# result is a NumpyBatchRecords instance

# Async
result = await async_client.batch_read(keys, bins=["score", "count"], _dtype=dtype)
```

### NumpyBatchRecords API

| Attribute / Method | Description |
|-------------------|-------------|
| `batch_records` | Structured numpy array with bin data |
| `meta` | `(gen, ttl)` structured array |
| `result_codes` | `int32` array (0 = success) |
| `get(key)` | Retrieve single record by primary key |
| `len(result)` | Number of records |
| `key in result` | Check if primary key exists |
| `for r in result` | Iterate over records |

### Access Data

```python
# Vectorized operations on the full array
avg_score = result.batch_records["score"].mean()
high_scorers = result.batch_records[result.batch_records["score"] > 90]

# Individual record by primary key
record = result.get("user_42")
print(record["score"], record["count"])

# Metadata arrays
print(result.meta["gen"])  # generation numbers
print(result.meta["ttl"])  # TTL values

# Result codes (0 = success)
success_mask = result.result_codes == 0
valid_records = result.batch_records[success_mask]
```

### Pandas Integration

```python
import pandas as pd

result = client.batch_read(keys, bins=["score", "count"], _dtype=dtype)

# Direct conversion -- zero copy for numeric data
df = pd.DataFrame(result.batch_records)
df["success"] = result.result_codes == 0
```

### Performance Tips

1. **Pre-allocate dtypes** -- Define dtype once and reuse across calls
2. **Match dtype to data** -- Use smallest sufficient type (`i4` vs `i8`, `f4` vs `f8`)
3. **Batch size** -- Optimal range: 500-5000 records per call
4. **Use fixed-length strings** -- `S16` is much faster than variable-length alternatives
5. **Filter server-side** -- Combine with expression filters to reduce data transfer

# Constants Reference

All constants are importable from `aerospike_py`.

## Table of Contents
- [Policy Constants](#policy-constants)
  - [Exists Policy](#exists-policy)
  - [Gen Policy](#gen-policy)
  - [Key Policy](#key-policy)
  - [Replica Policy](#replica-policy)
  - [Commit Level](#commit-level)
  - [Read Mode AP](#read-mode-ap)
- [TTL Constants](#ttl-constants)
- [Operator Constants](#operator-constants)
- [List Constants](#list-constants)
  - [List Return Type](#list-return-type)
  - [List Order / Sort / Write Flags](#list-order--sort--write-flags)
- [Map Constants](#map-constants)
  - [Map Return Type](#map-return-type)
  - [Map Order / Write Flags](#map-order--write-flags)
- [Bit & HLL Constants](#bit--hll-constants)
  - [Bit Write Flags](#bit-write-flags)
  - [Bit Resize Flags](#bit-resize-flags)
  - [Bit Overflow Action](#bit-overflow-action)
  - [HLL Write Flags](#hll-write-flags)
- [Index Constants](#index-constants)
  - [Index Data Type](#index-data-type)
  - [Index Collection Type](#index-collection-type)
- [Privilege Constants](#privilege-constants)
- [Auth & Log Constants](#auth--log-constants)
  - [Auth Mode](#auth-mode)
  - [Log Level](#log-level)
  - [Serializer](#serializer)

---

## Policy Constants

### Exists Policy

| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_EXISTS_IGNORE | 0 | Overwrite if exists, create if not (default) |
| POLICY_EXISTS_UPDATE | 1 | Update if exists, create if not |
| POLICY_EXISTS_UPDATE_ONLY | 1 | Error if record does not exist |
| POLICY_EXISTS_REPLACE | 2 | Replace entire record (deletes other bins) |
| POLICY_EXISTS_REPLACE_ONLY | 3 | Replace entire record, error if not exists |
| POLICY_EXISTS_CREATE_ONLY | 4 | Error if record already exists |

### Gen Policy

| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_GEN_IGNORE | 0 | Ignore generation (default) |
| POLICY_GEN_EQ | 1 | Write only if gen matches server gen |
| POLICY_GEN_GT | 2 | Write only if gen > server gen |

### Key Policy

| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_KEY_DIGEST | 0 | Store digest only (default) |
| POLICY_KEY_SEND | 1 | Store original key on server |

### Replica Policy

| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_REPLICA_MASTER | 0 | Read from master node only |
| POLICY_REPLICA_SEQUENCE | 1 | Sequential replica reads |
| POLICY_REPLICA_PREFER_RACK | 2 | Prefer same-rack node |

### Commit Level

| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_COMMIT_LEVEL_ALL | 0 | Commit to all replicas (default) |
| POLICY_COMMIT_LEVEL_MASTER | 1 | Commit to master only |

### Read Mode AP

| Constant | Value | Description |
|----------|-------|-------------|
| POLICY_READ_MODE_AP_ONE | 0 | Read from one node (default) |
| POLICY_READ_MODE_AP_ALL | 1 | Read from all nodes |

---

## TTL Constants

| Constant | Value | Description |
|----------|-------|-------------|
| TTL_NAMESPACE_DEFAULT | 0 | Use namespace default TTL |
| TTL_NEVER_EXPIRE | -1 | Record never expires |
| TTL_DONT_UPDATE | -2 | Do not change existing TTL |
| TTL_CLIENT_DEFAULT | -3 | Use client policy default |

---

## Operator Constants

For use with `operate()` and `operate_ordered()`.

| Constant | Value | Description |
|----------|-------|-------------|
| OPERATOR_READ | 1 | Read a bin |
| OPERATOR_WRITE | 2 | Write a bin |
| OPERATOR_INCR | 5 | Increment numeric bin |
| OPERATOR_APPEND | 9 | Append to string bin |
| OPERATOR_PREPEND | 10 | Prepend to string bin |
| OPERATOR_TOUCH | 11 | Reset record TTL |
| OPERATOR_DELETE | 12 | Delete record |

---

## List Constants

### List Return Type

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

### List Order / Sort / Write Flags

| Constant | Value | Description |
|----------|-------|-------------|
| LIST_UNORDERED | 0 | Unordered list |
| LIST_ORDERED | 1 | Ordered list |
| LIST_SORT_DEFAULT | 0 | Default sort |
| LIST_SORT_DROP_DUPLICATES | 2 | Drop duplicates on sort |
| LIST_WRITE_DEFAULT | 0 | Default write mode |
| LIST_WRITE_ADD_UNIQUE | 1 | Fail if value exists |
| LIST_WRITE_INSERT_BOUNDED | 2 | Enforce insert index bounds |
| LIST_WRITE_NO_FAIL | 4 | No error on policy violation |
| LIST_WRITE_PARTIAL | 8 | Allow partial success on batch |

---

## Map Constants

### Map Return Type

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

### Map Order / Write Flags

| Constant | Value | Description |
|----------|-------|-------------|
| MAP_UNORDERED | 0 | Unordered map |
| MAP_KEY_ORDERED | 1 | Key-ordered map |
| MAP_KEY_VALUE_ORDERED | 3 | Key-value-ordered map |
| MAP_WRITE_FLAGS_DEFAULT | 0 | Default write mode |
| MAP_WRITE_FLAGS_CREATE_ONLY | 1 | Error if key exists |
| MAP_WRITE_FLAGS_UPDATE_ONLY | 2 | Error if key does not exist |
| MAP_WRITE_FLAGS_NO_FAIL | 4 | No error on policy violation |
| MAP_WRITE_FLAGS_PARTIAL | 8 | Allow partial success on batch |
| MAP_UPDATE | 0 | Legacy alias for DEFAULT |
| MAP_UPDATE_ONLY | 2 | Legacy alias for UPDATE_ONLY |
| MAP_CREATE_ONLY | 1 | Legacy alias for CREATE_ONLY |

---

## Bit & HLL Constants

### Bit Write Flags

| Constant | Value | Description |
|----------|-------|-------------|
| BIT_WRITE_DEFAULT | 0 | Default write mode |
| BIT_WRITE_CREATE_ONLY | 1 | Error if bin exists |
| BIT_WRITE_UPDATE_ONLY | 2 | Error if bin does not exist |
| BIT_WRITE_NO_FAIL | 4 | No error on policy violation |
| BIT_WRITE_PARTIAL | 8 | Allow partial success |

### Bit Resize Flags

| Constant | Value | Description |
|----------|-------|-------------|
| BIT_RESIZE_DEFAULT | 0 | Default resize |
| BIT_RESIZE_FROM_FRONT | 1 | Resize from the front |
| BIT_RESIZE_GROW_ONLY | 2 | Only allow growing |
| BIT_RESIZE_SHRINK_ONLY | 4 | Only allow shrinking |

### Bit Overflow Action

| Constant | Value | Description |
|----------|-------|-------------|
| BIT_OVERFLOW_FAIL | 0 | Fail on overflow |
| BIT_OVERFLOW_SATURATE | 2 | Saturate on overflow |
| BIT_OVERFLOW_WRAP | 4 | Wrap on overflow |

### HLL Write Flags

| Constant | Value | Description |
|----------|-------|-------------|
| HLL_WRITE_DEFAULT | 0 | Default write mode |
| HLL_WRITE_CREATE_ONLY | 1 | Error if bin exists |
| HLL_WRITE_UPDATE_ONLY | 2 | Error if bin does not exist |
| HLL_WRITE_NO_FAIL | 4 | No error on policy violation |
| HLL_WRITE_ALLOW_FOLD | 8 | Allow fold on set-union |

---

## Index Constants

### Index Data Type

| Constant | Value | Description |
|----------|-------|-------------|
| INDEX_NUMERIC | 0 | Numeric index |
| INDEX_STRING | 1 | String index |
| INDEX_BLOB | 2 | Blob index |
| INDEX_GEO2DSPHERE | 3 | Geospatial index |

### Index Collection Type

| Constant | Value | Description |
|----------|-------|-------------|
| INDEX_TYPE_DEFAULT | 0 | Default (scalar bin) |
| INDEX_TYPE_LIST | 1 | List element index |
| INDEX_TYPE_MAPKEYS | 2 | Map key index |
| INDEX_TYPE_MAPVALUES | 3 | Map value index |

---

## Privilege Constants

| Constant | Value | Description |
|----------|-------|-------------|
| PRIV_USER_ADMIN | 0 | User admin |
| PRIV_SYS_ADMIN | 1 | System admin |
| PRIV_DATA_ADMIN | 2 | Data admin |
| PRIV_UDF_ADMIN | 3 | UDF admin |
| PRIV_SINDEX_ADMIN | 4 | Secondary index admin |
| PRIV_READ | 10 | Read privilege |
| PRIV_READ_WRITE | 11 | Read-write privilege |
| PRIV_READ_WRITE_UDF | 12 | Read-write with UDF |
| PRIV_WRITE | 13 | Write privilege |
| PRIV_TRUNCATE | 14 | Truncate privilege |

---

## Auth & Log Constants

### Auth Mode

| Constant | Value | Description |
|----------|-------|-------------|
| AUTH_INTERNAL | 0 | Internal authentication |
| AUTH_EXTERNAL | 1 | External (LDAP) authentication |
| AUTH_PKI | 2 | PKI mutual TLS authentication |

### Log Level

| Constant | Value | Description |
|----------|-------|-------------|
| LOG_LEVEL_OFF | -1 | Logging disabled |
| LOG_LEVEL_ERROR | 0 | Error messages only |
| LOG_LEVEL_WARN | 1 | Warnings and above |
| LOG_LEVEL_INFO | 2 | Info and above |
| LOG_LEVEL_DEBUG | 3 | Debug and above |
| LOG_LEVEL_TRACE | 4 | All messages |

### Serializer

| Constant | Value | Description |
|----------|-------|-------------|
| SERIALIZER_NONE | 0 | No serialization |
| SERIALIZER_PYTHON | 1 | Python pickle serialization |
| SERIALIZER_USER | 2 | User-defined serialization |

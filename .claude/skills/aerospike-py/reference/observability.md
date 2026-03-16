# Observability Reference

## Table of Contents
- [Logging](#logging)
- [Prometheus Metrics](#prometheus-metrics)
- [OpenTelemetry Tracing](#opentelemetry-tracing)

---

## Logging

Built-in Rust-to-Python logging bridge that forwards all internal Rust logs to Python's `logging` module. Initialized automatically on import.

### Log Levels

| Constant | Value | Python Level | Description |
|----------|-------|--------------|-------------|
| LOG_LEVEL_OFF | -1 | (disabled) | No logging |
| LOG_LEVEL_ERROR | 0 | ERROR (40) | Errors only |
| LOG_LEVEL_WARN | 1 | WARNING (30) | Warnings and above |
| LOG_LEVEL_INFO | 2 | INFO (20) | Info and above (default) |
| LOG_LEVEL_DEBUG | 3 | DEBUG (10) | Debug and above |
| LOG_LEVEL_TRACE | 4 | TRACE (5) | All messages (verbose) |

### API

| Function | Description |
|----------|-------------|
| set_log_level(level: int) | Set Rust logger level |

```python
import logging
import aerospike_py

logging.basicConfig(level=logging.DEBUG)
aerospike_py.set_log_level(aerospike_py.LOG_LEVEL_DEBUG)
```

### Logger Names

| Logger | Description |
|--------|-------------|
| `aerospike_core::cluster` | Cluster discovery, node management |
| `aerospike_core::batch` | Batch operation execution |
| `aerospike_core::command` | Individual command execution |
| `aerospike_py` | Python-side client wrapper |

```python
# Fine-grained control
logging.getLogger("aerospike_core::cluster").setLevel(logging.DEBUG)
logging.getLogger("aerospike_core::batch").setLevel(logging.WARNING)
```

### JSON Logging Setup

```python
import logging, json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("aerospike_core")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
```

### Disabling

```python
aerospike_py.set_log_level(aerospike_py.LOG_LEVEL_OFF)
```

---

## Prometheus Metrics

Operation-level metrics collected in Rust and exposed in Prometheus text format. Metric names follow OpenTelemetry DB Client Semantic Conventions.

### API

| Function | Description |
|----------|-------------|
| start_metrics_server(port=9464) | Start background HTTP server at `/metrics` |
| get_metrics() -> str | Get current metrics in Prometheus text format |
| stop_metrics_server() | Stop the metrics server |

```python
import aerospike_py

# Get metrics as string
text: str = aerospike_py.get_metrics()

# Or start a built-in HTTP server
aerospike_py.start_metrics_server(port=9464)
# Prometheus scrapes http://localhost:9464/metrics

# Stop when done
aerospike_py.stop_metrics_server()
```

### Metric: `db_client_operation_duration_seconds` (histogram)

**Labels:**

| Label | Examples |
|-------|---------|
| db_system_name | `aerospike` |
| db_namespace | `test`, `production` |
| db_collection_name | `users`, `sessions` |
| db_operation_name | `get`, `put`, `delete`, `query` |
| error_type | `""` (success), `Timeout`, `KeyNotFoundError` |

**Buckets:** `0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0` seconds

**Instrumented operations:** `put`, `get`, `select`, `exists`, `remove`, `touch`, `append`, `prepend`, `increment`, `operate`, `batch_read`, `batch_operate`, `batch_remove`, `query`

Note: `exists()` treats `KeyNotFoundError` as success since "not found" is a normal outcome.

### PromQL Examples

```promql
# Average latency (5m)
rate(db_client_operation_duration_seconds_sum[5m])
/ rate(db_client_operation_duration_seconds_count[5m])

# P99 latency
histogram_quantile(0.99, rate(db_client_operation_duration_seconds_bucket[5m]))

# Error rate by type
sum by (error_type) (rate(db_client_operation_duration_seconds_count{error_type!=""}[5m]))

# Ops/sec by namespace
sum by (db_namespace, db_operation_name) (rate(db_client_operation_duration_seconds_count[1m]))
```

### Grafana Dashboard Panels

| Panel | PromQL | Type |
|-------|--------|------|
| Ops/sec | `sum(rate(..._count[1m])) by (db_operation_name)` | Time series |
| P50/P95/P99 | `histogram_quantile(0.5\|0.95\|0.99, rate(..._bucket[5m]))` | Time series |
| Error Rate | `sum(rate(..._count{error_type!=""}[1m])) by (error_type)` | Time series |
| By Namespace | `sum(rate(..._count[1m])) by (db_namespace)` | Pie chart |

### Performance

| Scenario | Overhead |
|----------|----------|
| Per-operation recording | ~30-80 ns (atomic increment) |
| Relative to network round-trip | 0.001-0.01% |
| `get_metrics()` encoding | ~50-200 us |

Metrics collection is always enabled with negligible overhead.

---

## OpenTelemetry Tracing

Built-in OpenTelemetry tracing for every data operation. Spans follow Database Client Semantic Conventions and export via OTLP gRPC.

### Setup

```bash
pip install aerospike-py            # tracing built-in
pip install aerospike-py[otel]      # + context propagation from Python spans
```

### API

| Function | Description |
|----------|-------------|
| init_tracing() | Initialize OTel tracing (reads `OTEL_*` env vars) |
| shutdown_tracing() | Flush and shut down. Call before process exit. |

Both are thread-safe and idempotent.

```python
import aerospike_py

aerospike_py.init_tracing()

client = aerospike_py.client({"hosts": [("127.0.0.1", 3000)]}).connect()
client.put(("test", "users", "user1"), {"name": "Alice"})
client.get(("test", "users", "user1"))
client.close()

aerospike_py.shutdown_tracing()
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OTEL_EXPORTER_OTLP_ENDPOINT | `http://localhost:4317` | OTLP gRPC endpoint |
| OTEL_SERVICE_NAME | `aerospike-py` | Service name for spans |
| OTEL_SDK_DISABLED | `false` | Disable tracing entirely |
| OTEL_TRACES_EXPORTER | `otlp` | Set to `none` to disable export |

### Span Attributes

| Attribute | Example |
|-----------|---------|
| db.system.name | `aerospike` |
| db.namespace | `test` |
| db.collection.name | `users` |
| db.operation.name | `PUT`, `GET`, `REMOVE` |

**Span name:** `{OPERATION} {namespace}.{set}` (e.g., `PUT test.users`)

**On error:** `error.type`, `db.response.status_code`, `otel.status_code=ERROR`

**Instrumented:** `put`, `get`, `select`, `exists`, `remove`, `touch`, `append`, `prepend`, `increment`, `operate`, `batch_read`, `batch_operate`, `batch_remove`, `query`

### W3C TraceContext Propagation

With `aerospike-py[otel]` installed, W3C TraceContext is automatically propagated from Python active spans to Rust spans:

| Setup | Behavior |
|-------|----------|
| `aerospike-py[otel]` + active span | Python span becomes parent |
| `aerospike-py[otel]` + no active span | Root span created |
| `aerospike-py` (base) | Root span (no propagation) |

### Disabling

```bash
export OTEL_SDK_DISABLED=true          # disable entirely
export OTEL_TRACES_EXPORTER=none       # spans created but not exported
```

### Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| OTLP endpoint unreachable | Warning log, tracing disabled |
| `init_tracing()` not called | No-op spans |
| `opentelemetry-api` not installed | Root spans (no propagation) |
| `shutdown_tracing()` not called | Some pending spans may be lost |

### Performance

| Scenario | Overhead |
|----------|----------|
| Span creation | ~1-5 us |
| Context propagation | ~10-50 us |
| vs network round-trip | < 1% |
| `OTEL_SDK_DISABLED=true` | ~30-80 ns (metrics only) |

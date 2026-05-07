"""Business logic for ad-hoc Aerospike queries.

This module backs the ``POST /query/{conn_id}`` endpoint. It is the single
source of truth for query execution and is called by both:

* the HTTP router (``routers/query.py``) — which wraps the result in
  HTTPException translation, FastAPI dependencies, and ``record_to_model``
  conversion to the wire-format ``AerospikeRecord``, and
* the MCP tool layer (added in a later task) — which calls it directly from
  MCP tool handlers.

To stay reusable from both sides, this module **must not** import ``fastapi``
or other HTTP-shaping libraries. Domain failures are signalled by plain
exceptions defined here, which the router translates to HTTP status codes.

CDT (lists, maps, geojson) bin values are returned as the raw aerospike-py
``Record`` NamedTuple — JSON-safe serialization is intentionally deferred to
the dedicated serializer layer (Phase 1 task A.10), so this module never
mutates bin contents.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal, NamedTuple

import aerospike_py
from aerospike_py import Record
from aerospike_py.exception import AerospikeError, RecordNotFound

from aerospike_cluster_manager_api.constants import MAX_QUERY_RECORDS, POLICY_QUERY, POLICY_READ
from aerospike_cluster_manager_api.models.query import QueryRequest

logger = logging.getLogger(__name__)


# Explicit PK particle type selector. ``auto`` is a heuristic that tries the
# most likely type then falls back on RecordNotFound. Same shape as the
# records_service equivalent.
PkType = Literal["auto", "string", "int", "bytes"]


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class SetRequiredForPkLookup(ValueError):
    """Raised when a PK lookup is run without a ``set`` scope.

    Aerospike addresses records via ``(namespace, set, pk)`` tuples, so a PK
    lookup without a set is meaningless. Disallowed at the service boundary.
    """

    def __init__(self) -> None:
        super().__init__("Set is required for primary key lookup")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


class QueryResult(NamedTuple):
    """Outcome of a query/scan call.

    ``records`` is a list of raw aerospike-py ``Record`` NamedTuples. The
    router converts each one via ``converters.record_to_model`` before
    returning to clients; CDT-safe serialization is left to a dedicated
    serializer layer.

    ``scanned_records`` and ``returned_records`` are equal in this layer
    because the underlying aerospike-py scan does not expose an exact count
    distinct from the returned records once ``max_records`` is applied. They
    are kept as separate fields to mirror the wire-format ``QueryResponse``.
    """

    records: list[Record]
    execution_time_ms: int
    scanned_records: int
    returned_records: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_pk(pk: str, pk_type: PkType) -> str | int | bytes:
    """Resolve a string primary key into the typed value Aerospike expects.

    Mirrors ``utils.resolve_pk`` but raises ``ValueError`` instead of
    HTTPException so the service stays HTTP-free. The router catches the
    ``ValueError`` and translates it to HTTP 400.
    """
    if pk_type == "string":
        return pk
    if pk_type == "int":
        try:
            return int(pk)
        except ValueError as exc:
            raise ValueError(f"pk_type=int but pk is not an integer: {pk!r}") from exc
    if pk_type == "bytes":
        try:
            return bytes.fromhex(pk)
        except ValueError as exc:
            raise ValueError(f"pk_type=bytes but pk is not valid hex: {pk!r}") from exc

    # ``auto``: numeric-string heuristic. Preserves leading-zero strings.
    try:
        as_int = int(pk)
        if str(as_int) == pk:
            return as_int
    except ValueError:
        pass
    return pk


async def _get_with_pk_fallback(
    client: aerospike_py.AsyncClient,
    key_tuple: tuple[str, str, str | int | bytes],
    pk_raw: str,
    pk_type: PkType,
    policy: dict[str, Any],
) -> Record:
    """Read with retry-on-NOT-FOUND for ``auto`` PK type.

    When ``pk_type == "auto"`` and the first attempt raises
    ``RecordNotFound``, retry with the alternate string/int particle type
    (whichever the heuristic did *not* pick). Explicit pk types never fall
    back — propagate the NOT_FOUND so callers see a genuinely absent key.
    """
    try:
        return await client.get(key_tuple, policy=policy)
    except RecordNotFound:
        if pk_type != "auto":
            raise
        first = key_tuple[2]
        alt: str | int | None = None
        if isinstance(first, int):
            alt = pk_raw  # retry as raw string
        elif isinstance(first, str):
            try:
                alt = int(first)
            except ValueError:
                alt = None
        if alt is None:
            raise
        return await client.get((key_tuple[0], key_tuple[1], alt), policy=policy)


# ---------------------------------------------------------------------------
# Service entry point
# ---------------------------------------------------------------------------


async def execute_query(client: aerospike_py.AsyncClient, body: QueryRequest) -> QueryResult:
    """Execute a query against Aerospike.

    Two execution paths, selected by ``body.primaryKey``:

    1. **PK lookup** — when ``body.primaryKey`` is set. Resolves the PK via
       ``body.pkType`` (``"auto"`` retries the alternate particle type on
       NOT_FOUND so numeric-string keys are resolvable even when the
       heuristic guesses int). Returns at most one record. ``RecordNotFound``
       is treated as an empty result rather than propagating.

    2. **Scan** — when no ``primaryKey``. Optionally applies a predicate
       (legacy secondary-index path) and a ``select_bins`` projection. The
       server-side ``max_records`` policy is capped at ``MAX_QUERY_RECORDS``
       to prevent OOM. Empty/sparse namespaces can make the underlying scan
       raise (aerospike-py issue #259) — those are caught and surfaced as
       an empty result instead of a 500.

    Raises:
        SetRequiredForPkLookup: ``primaryKey`` provided without a ``set``.
        ValueError: explicit ``pkType`` rejected the resolved value.

    Returns:
        ``QueryResult`` with raw aerospike-py ``Record`` NamedTuples. The
        router converts each one via ``record_to_model`` for the wire format.
    """
    start_time = time.monotonic()

    # ---- PK lookup branch -------------------------------------------------
    if body.primaryKey:
        if not body.set:
            raise SetRequiredForPkLookup()

        resolved = _resolve_pk(body.primaryKey, body.pkType)
        try:
            raw_record = await _get_with_pk_fallback(
                client,
                (body.namespace, body.set, resolved),
                body.primaryKey,
                body.pkType,
                POLICY_READ,
            )
            raw_results: list[Record] = [raw_record]
        except RecordNotFound:
            raw_results = []

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return QueryResult(
            records=raw_results,
            execution_time_ms=elapsed_ms,
            scanned_records=len(raw_results),
            returned_records=len(raw_results),
        )

    # ---- Scan branch ------------------------------------------------------
    q = client.query(body.namespace, body.set or "")
    if body.predicate:
        # Local import keeps utils.build_predicate's HTTPException-aware
        # implementation out of the service's signature surface. The router
        # catches ``HTTPException`` directly; service callers via MCP would
        # surface the exception as a generic error.
        from aerospike_cluster_manager_api.utils import build_predicate

        q.where(build_predicate(body.predicate))
    if body.selectBins:
        q.select(*body.selectBins)

    # Apply server-side max_records limit to prevent OOM. With max_records
    # the server stops after returning this many matching records, so
    # scanned_records reflects the returned count (lower bound), not the true
    # number of records examined by the server.
    effective_limit = min(body.maxRecords or MAX_QUERY_RECORDS, MAX_QUERY_RECORDS)
    policy: dict[str, Any] = {**POLICY_QUERY, "max_records": effective_limit}

    # See aerospike-py issue #259: empty / sparse namespaces can make the
    # underlying scan raise. Treat as no records rather than 500.
    try:
        raw_results = await q.results(policy)
    except AerospikeError:
        logger.exception(
            "Query failed for ns=%s set=%s; returning empty result",
            body.namespace,
            body.set,
        )
        raw_results = []

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    return QueryResult(
        records=raw_results,
        execution_time_ms=elapsed_ms,
        scanned_records=len(raw_results),
        returned_records=len(raw_results),
    )

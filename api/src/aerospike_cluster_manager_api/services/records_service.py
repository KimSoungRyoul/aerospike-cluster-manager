"""Business logic for Aerospike record CRUD and scan operations.

These functions are the single source of truth for the records read/write
path. They are called by both:

* the HTTP router (``routers/records.py``) — which wraps them in
  HTTPException translation, FastAPI dependencies, and ``record_to_model``
  conversion to the wire-format ``AerospikeRecord``, and
* the MCP tool layer (added in a later task) — which calls them directly
  from MCP tool handlers.

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
from aerospike_py import Record, exp
from aerospike_py.exception import AerospikeError, RecordNotFound
from aerospike_py.types import WriteMeta

from aerospike_cluster_manager_api.constants import (
    MAX_QUERY_RECORDS,
    POLICY_QUERY,
    POLICY_READ,
    POLICY_WRITE,
    info_namespace,
    info_sets,
)
from aerospike_cluster_manager_api.expression_builder import (
    InvalidPkPatternError,
    build_expression,
    build_pk_filter_expression,
)
from aerospike_cluster_manager_api.info_parser import (
    aggregate_node_kv,
    aggregate_set_records,
    safe_int,
)
from aerospike_cluster_manager_api.models.query import FilteredQueryRequest
from aerospike_cluster_manager_api.models.record import RecordWriteRequest

logger = logging.getLogger(__name__)


# Explicit PK particle type selector. ``auto`` is a heuristic that tries the
# most likely type then falls back on RecordNotFound. See ``utils.resolve_pk``
# for the resolution rules.
PkType = Literal["auto", "string", "int", "bytes"]


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class InvalidPkPattern(ValueError):
    """Raised when a PK pattern (prefix/regex) cannot be compiled."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SetRequiredForPkLookup(ValueError):
    """Raised when a PK-targeted query is run without a ``set`` scope.

    An unscoped namespace scan with a regex would dwarf the user's intent and
    is disallowed at the service boundary.
    """

    def __init__(self) -> None:
        super().__init__("Set is required for primary key lookup")


class PrimaryKeyMissing(ValueError):
    """Raised when a write request omits one of namespace/set/pk."""

    def __init__(self, field: str) -> None:
        super().__init__(f"Missing required key field: {field}")
        self.field = field


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


class ListRecordsResult(NamedTuple):
    """Outcome of a paginated list/scan call.

    ``records`` is a list of raw aerospike-py ``Record`` NamedTuples. The
    router converts each one via ``converters.record_to_model`` before
    returning to clients; CDT-safe serialization is left to a dedicated
    serializer layer.
    """

    records: list[Record]
    total: int
    page: int
    page_size: int
    has_more: bool
    total_estimated: bool


class FilterRecordsResult(NamedTuple):
    """Outcome of a paginated filter/scan call.

    ``scanned_records`` and ``returned_records`` are lower bounds when
    ``total_estimated`` is True (the server-side filter scan does not
    expose an exact count without a separate count-only query).
    """

    records: list[Record]
    total: int
    page: int
    page_size: int
    has_more: bool
    execution_time_ms: int
    scanned_records: int
    returned_records: int
    total_estimated: bool


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


async def _get_set_object_count(client: aerospike_py.AsyncClient, ns: str, set_name: str) -> int:
    """Approximate object count for a set via the namespace/sets info commands.

    Fetches the namespace replication-factor first to de-duplicate counts
    across nodes, matching the same approach used in ``clusters_service``.
    """
    if not set_name:
        return 0
    try:
        ns_all = await client.info_all(info_namespace(ns))
        ns_stats = aggregate_node_kv(ns_all)
        replication_factor = safe_int(ns_stats.get("replication-factor"), 1)

        sets_all = await client.info_all(info_sets(ns))
        agg = aggregate_set_records(sets_all, replication_factor)
        for s in agg:
            if s["name"] == set_name:
                return s["objects"]
    except (AerospikeError, OSError):
        logger.debug("Failed to get set object count for %s.%s", ns, set_name, exc_info=True)
    return 0


# ---------------------------------------------------------------------------
# Service entry points — single record CRUD
# ---------------------------------------------------------------------------


async def get_record(
    client: aerospike_py.AsyncClient,
    namespace: str,
    set_name: str,
    pk: str,
    pk_type: PkType = "auto",
) -> Record:
    """Fetch a single record by ``(namespace, set, pk)``.

    Resolves ``pk`` via the requested ``pk_type``. When ``pk_type='auto'``
    and the initial probe returns NOT_FOUND, retries with the alternate
    particle type — fixing the case where a numeric-string key (e.g. ``"42"``)
    was stored as STRING but auto resolves to INTEGER.

    Raises:
        RecordNotFound: the record does not exist (after auto fallback).
        ValueError: ``pk_type`` was explicit but ``pk`` could not be parsed.
    """
    resolved = _resolve_pk(pk, pk_type)
    return await _get_with_pk_fallback(client, (namespace, set_name, resolved), pk, pk_type, POLICY_READ)


async def delete_record(
    client: aerospike_py.AsyncClient,
    namespace: str,
    set_name: str,
    pk: str,
    pk_type: PkType = "auto",
) -> None:
    """Delete a record by ``(namespace, set, pk)``.

    Deletes do not fall back to the alternate type even in ``auto`` mode: a
    delete that targets the wrong particle type would silently no-op (the
    record at the *other* type stays put), and a fallback could mask that
    fact. Pass an explicit ``pk_type`` to be sure of which record gets removed.

    Raises:
        RecordNotFound: aerospike-py may surface this when the key does not
            exist; callers may treat it as a 404 or a 204 depending on the
            HTTP semantics they want.
        ValueError: ``pk_type`` was explicit but ``pk`` could not be parsed.
    """
    resolved = _resolve_pk(pk, pk_type)
    await client.remove((namespace, set_name, resolved))


async def put_record(client: aerospike_py.AsyncClient, body: RecordWriteRequest) -> Record:
    """Write a record (create or update) and return the persisted state.

    The key's particle type comes from ``body.pk_type`` (``"auto"`` by default).
    Writes do not fall back: the resolved type is what gets persisted on disk,
    so callers that care should pass an explicit ``pk_type`` to avoid creating
    a record under a particle type that subsequent reads can't find.

    Returns:
        The freshly read-back ``Record`` so the response can carry the
        server-assigned generation/ttl.

    Raises:
        PrimaryKeyMissing: ``body.key`` omits namespace, set, or pk.
        ValueError: explicit ``pk_type`` rejected the resolved value.
    """
    k = body.key
    if not k.namespace:
        raise PrimaryKeyMissing("namespace")
    if not k.set:
        raise PrimaryKeyMissing("set")
    if not k.pk:
        raise PrimaryKeyMissing("pk")

    key_tuple = (k.namespace, k.set, _resolve_pk(k.pk, body.pk_type))

    meta: WriteMeta | None = None
    if body.ttl is not None:
        meta = WriteMeta(ttl=body.ttl)

    await client.put(key_tuple, body.bins, meta=meta, policy=POLICY_WRITE)
    return await client.get(key_tuple, policy=POLICY_READ)


# ---------------------------------------------------------------------------
# Service entry points — list / filter scans
# ---------------------------------------------------------------------------


async def list_records(
    client: aerospike_py.AsyncClient,
    namespace: str,
    set_name: str,
    page_size: int,
) -> ListRecordsResult:
    """Scan a set and return up to ``page_size`` records.

    Empty / sparse namespaces can make the underlying scan raise
    (aerospike-py issue #259). Treat those as "no records" and return an
    empty page rather than propagate. ``RustPanicError`` (#280) is *not*
    caught here — that's a real per-stream blocker handled by its dedicated
    422 exception handler at the HTTP layer.
    """
    set_total = await _get_set_object_count(client, namespace, set_name)

    limit = min(page_size, MAX_QUERY_RECORDS)
    policy: dict[str, Any] = {**POLICY_QUERY, "max_records": limit}
    q = client.query(namespace, set_name)
    try:
        raw_results: list[Record] = await q.results(policy)
    except AerospikeError:
        logger.exception("Query failed for ns=%s set=%s; returning empty page", namespace, set_name)
        raw_results = []

    return ListRecordsResult(
        records=raw_results,
        total=set_total,
        page=1,
        page_size=page_size,
        has_more=set_total > len(raw_results),
        total_estimated=True,
    )


async def filter_records(client: aerospike_py.AsyncClient, body: FilteredQueryRequest) -> FilterRecordsResult:
    """Scan with optional PK pattern + bin filters and return a page.

    PK lookup short-circuits to ``client.get`` when ``pk_match_mode='exact'``
    so a pure-key fetch never triggers a scan. ``prefix`` and ``regex`` modes
    compile the PK pattern into an expression and run a server-side scan.

    Raises:
        SetRequiredForPkLookup: PK pattern provided without a set scope.
        InvalidPkPattern: regex/prefix could not be compiled.
    """
    start_time = time.monotonic()

    pk_target = body.pk_pattern or body.primary_key

    if pk_target and not body.set:
        raise SetRequiredForPkLookup()

    # PK exact short-circuit. Falls back to alternate particle type on
    # NOT_FOUND when pk_type='auto'. Prefix/regex skip this branch.
    if pk_target and body.pk_match_mode == "exact":
        assert body.set is not None
        resolved = _resolve_pk(pk_target, body.pk_type)
        try:
            raw_record = await _get_with_pk_fallback(
                client,
                (body.namespace, body.set, resolved),
                pk_target,
                body.pk_type,
                POLICY_READ,
            )
            raw_results: list[Record] = [raw_record]
        except RecordNotFound:
            raw_results = []

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return FilterRecordsResult(
            records=raw_results,
            total=len(raw_results),
            page=1,
            page_size=body.page_size,
            has_more=False,
            execution_time_ms=elapsed_ms,
            scanned_records=len(raw_results),
            returned_records=len(raw_results),
            total_estimated=False,
        )

    # Build expressions BEFORE constructing the query so a bad pattern
    # surfaces as InvalidPkPattern without ever touching the client.query
    # path (and lets the router translate to HTTP 400).
    pk_expr: dict | None = None
    try:
        if pk_target is not None:
            if body.pk_match_mode == "prefix":
                pk_expr = build_pk_filter_expression(pk_target, "prefix")
            elif body.pk_match_mode == "regex":
                pk_expr = build_pk_filter_expression(pk_target, "regex")
    except InvalidPkPatternError as e:
        raise InvalidPkPattern(str(e)) from e

    bin_expr = build_expression(body.filters) if body.filters else None

    # Build query
    q = client.query(body.namespace, body.set or "")

    if body.predicate:
        # Local import keeps utils.build_predicate's HTTPException-aware
        # implementation out of the service's signature surface.
        from aerospike_cluster_manager_api.utils import build_predicate

        q.where(build_predicate(body.predicate))

    if body.select_bins:
        q.select(*body.select_bins)

    # Build policy with server-side max_records limit to prevent OOM.
    #
    # For paginated filter queries we fetch ONE extra record beyond the page
    # size so we can detect "is there at least one more record" without an
    # extra round trip. The fetched +1 record is dropped before responding.
    has_filters = body.filters is not None or body.predicate is not None or pk_expr is not None
    fetch_limit = min(
        body.max_records or MAX_QUERY_RECORDS,
        MAX_QUERY_RECORDS,
        body.page_size + 1,
    )

    policy: dict[str, Any] = {**POLICY_QUERY, "max_records": fetch_limit}
    if bin_expr is not None and pk_expr is not None:
        policy["filter_expression"] = exp.and_(pk_expr, bin_expr)
    elif pk_expr is not None:
        policy["filter_expression"] = pk_expr
    elif bin_expr is not None:
        policy["filter_expression"] = bin_expr

    try:
        raw_results = await q.results(policy)
    except AerospikeError:
        # Empty/sparse-namespace failure mode (aerospike-py #259). Log at
        # exception level so operators can still find the underlying cause
        # in logs — pattern + filter context goes in the message so user-
        # supplied PK patterns are reproducible.
        logger.exception(
            "Filtered query failed for ns=%s set=%s pk_mode=%s pk_pattern=%r has_filters=%s; returning empty page",
            body.namespace,
            body.set,
            body.pk_match_mode,
            pk_target,
            body.filters is not None,
        )
        raw_results = []

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    fetched = len(raw_results)
    has_more = fetched > body.page_size
    if has_more:
        raw_results = raw_results[: body.page_size]
    returned = len(raw_results)

    # Determine total / scanned counts. With server-side max_records the
    # returned count is capped — it does not reflect the true number of
    # records scanned by the Aerospike server. For unfiltered scans we use
    # the info command to get the real set size.
    if has_filters:
        set_total = returned + (1 if has_more else 0)  # lower bound
        scanned = returned  # lower bound; actual server-side scan may be higher
        total_estimated = True
    else:
        set_total = await _get_set_object_count(client, body.namespace, body.set or "")
        scanned = set_total  # info-based: represents all objects in the set
        total_estimated = True

    return FilterRecordsResult(
        records=raw_results,
        total=set_total,
        page=1,
        page_size=body.page_size,
        has_more=has_more,
        execution_time_ms=elapsed_ms,
        scanned_records=scanned,
        returned_records=returned,
        total_estimated=total_estimated,
    )

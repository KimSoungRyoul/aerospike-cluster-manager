"""MCP query tool — runs PK lookup or predicate scan via ``query_service``."""

from __future__ import annotations

from typing import Any, Literal

import aerospike_py

from aerospike_cluster_manager_api.client_manager import client_manager
from aerospike_cluster_manager_api.constants import MAX_QUERY_RECORDS
from aerospike_cluster_manager_api.mcp.registry import tool
from aerospike_cluster_manager_api.mcp.serializers import serialize_record
from aerospike_cluster_manager_api.models.query import QueryPredicate, QueryRequest
from aerospike_cluster_manager_api.services import query_service
from aerospike_cluster_manager_api.services.connections_service import ConnectionNotFoundError


async def _get_client(conn_id: str) -> aerospike_py.AsyncClient:
    try:
        return await client_manager.get_client(conn_id)
    except ValueError as e:
        raise ConnectionNotFoundError(conn_id) from e


@tool(category="query", mutation=False)
async def query(
    conn_id: str,
    namespace: str,
    set_name: str | None = None,
    primary_key: str | None = None,
    predicate_bin: str | None = None,
    predicate_operator: Literal["equals", "between", "contains", "geo_within_region", "geo_contains_point"]
    | None = None,
    predicate_value: Any = None,
    predicate_value2: Any = None,
    select_bins: list[str] | None = None,
    max_records: int | None = 100,
    pk_type: Literal["auto", "string", "int", "bytes"] = "auto",
) -> dict[str, Any]:
    """Run a query: PK lookup if ``primary_key`` is provided, otherwise a scan.

    Predicate scans are described inline via ``predicate_bin``,
    ``predicate_operator``, ``predicate_value`` (and optionally
    ``predicate_value2`` for ``between``). Both ``predicate_bin`` and
    ``predicate_operator`` must be supplied together — partial input is
    rejected.

    Returns ``{"records": [...], "execution_time_ms": int, "scanned_records":
    int, "returned_records": int, "truncated": bool}``. ``truncated`` is True
    when the service capped the result at the effective ``max_records`` limit
    (``min(max_records, MAX_QUERY_RECORDS)``); the model should re-issue with
    a tighter filter or a higher ``max_records`` to retrieve the rest. Records
    are serialised via :func:`mcp.serializers.serialize_record` so binary,
    GeoJSON, and CDT bins round-trip through JSON safely.
    """
    client = await _get_client(conn_id)

    pred_model: QueryPredicate | None = None
    if predicate_bin is not None or predicate_operator is not None:
        if predicate_bin is None or predicate_operator is None:
            raise ValueError("predicate_bin and predicate_operator must be provided together")
        pred_model = QueryPredicate(
            bin=predicate_bin,
            operator=predicate_operator,
            value=predicate_value,
            value2=predicate_value2,
        )

    body = QueryRequest(
        namespace=namespace,
        set=set_name,
        predicate=pred_model,
        selectBins=select_bins,
        maxRecords=max_records,
        primaryKey=primary_key,
        pkType=pk_type,
    )
    result = await query_service.execute_query(client, body)

    # Truncation signal: the service caps results at
    # ``min(max_records or MAX_QUERY_RECORDS, MAX_QUERY_RECORDS)``. When the
    # returned count hits that cap, more records likely exist server-side.
    # Phase 1-B's service layer does not expose an explicit "truncated"
    # field yet, so we compute it from the request-side cap math.
    effective_limit = min(max_records or MAX_QUERY_RECORDS, MAX_QUERY_RECORDS)
    truncated = result.returned_records >= effective_limit

    return {
        "records": [serialize_record(r) for r in result.records],
        "execution_time_ms": result.execution_time_ms,
        "scanned_records": result.scanned_records,
        "returned_records": result.returned_records,
        "truncated": truncated,
    }

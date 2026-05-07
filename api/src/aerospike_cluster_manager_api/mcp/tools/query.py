"""MCP query tool — runs PK lookup or predicate scan via ``query_service``."""

from __future__ import annotations

from typing import Any

import aerospike_py

from aerospike_cluster_manager_api.client_manager import client_manager
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
    predicate: dict[str, Any] | None = None,
    select_bins: list[str] | None = None,
    max_records: int | None = 100,
    pk_type: str = "auto",
) -> dict[str, Any]:
    """Run a query: PK lookup if ``primary_key`` is provided, otherwise a scan.

    Returns ``{"records": [...], "execution_time_ms": int, "scanned_records":
    int, "returned_records": int}``. Records are serialised via
    :func:`mcp.serializers.serialize_record` so binary, GeoJSON, and CDT
    bins round-trip through JSON safely.
    """
    client = await _get_client(conn_id)

    pred_model = QueryPredicate.model_validate(predicate) if predicate is not None else None
    body = QueryRequest(
        namespace=namespace,
        set=set_name,
        predicate=pred_model,
        selectBins=select_bins,
        maxRecords=max_records,
        primaryKey=primary_key,
        pkType=pk_type,  # type: ignore[arg-type]
    )
    result = await query_service.execute_query(client, body)
    return {
        "records": [serialize_record(r) for r in result.records],
        "execution_time_ms": result.execution_time_ms,
        "scanned_records": result.scanned_records,
        "returned_records": result.returned_records,
    }

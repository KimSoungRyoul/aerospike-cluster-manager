"""MCP info command tools — ``execute_info`` and ``execute_info_on_node``.

Both are classified as **mutation** in :mod:`mcp.access_profile` because
asinfo can change cluster configuration (``set-config``, ``recluster``,
etc.). Under ``READ_ONLY`` profile they are blocked at call time.
"""

from __future__ import annotations

from typing import Any

import aerospike_py

from aerospike_cluster_manager_api.client_manager import client_manager
from aerospike_cluster_manager_api.mcp.registry import tool
from aerospike_cluster_manager_api.services import clusters_service
from aerospike_cluster_manager_api.services.connections_service import ConnectionNotFoundError


async def _get_client(conn_id: str) -> aerospike_py.AsyncClient:
    try:
        return await client_manager.get_client(conn_id)
    except ValueError as e:
        raise ConnectionNotFoundError(conn_id) from e


@tool(category="info", mutation=True)
async def execute_info(conn_id: str, command: str) -> dict[str, Any]:
    """Run an asinfo command on every node and return per-node responses.

    Returns ``{"nodes": [{"node": str, "error_code": int | None, "response":
    str}, ...]}``.
    """
    client = await _get_client(conn_id)
    results = await clusters_service.execute_info(client, command)
    return {"nodes": [{"node": r.node_name, "error_code": r.error_code, "response": r.response} for r in results]}


@tool(category="info", mutation=True)
async def execute_info_on_node(conn_id: str, command: str, node_name: str) -> dict[str, str]:
    """Run an asinfo command on a single node and return the response."""
    client = await _get_client(conn_id)
    response = await clusters_service.execute_info_on_node(client, command, node_name)
    return {"node": node_name, "response": response}

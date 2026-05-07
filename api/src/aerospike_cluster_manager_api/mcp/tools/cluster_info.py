"""MCP tools for Aerospike cluster inspection.

This module exposes 3 read-only tools that wrap the existing service layer
(:mod:`aerospike_cluster_manager_api.services.clusters_service`) and the
live-client pool (:mod:`aerospike_cluster_manager_api.client_manager`):

* ``list_namespaces`` — namespace names defined on the cluster
* ``list_sets`` — per-set object/byte counts within a namespace
* ``get_nodes`` — per-node build/edition/uptime/connection metadata

Design notes:

* All 3 tools require an explicit ``conn_id`` — there's no implicit "default
  cluster" fallback; every cluster-scoped call names its cluster.
* ``client_manager.get_client`` raises :class:`ValueError` when the profile
  is missing; we re-raise as :class:`ConnectionNotFoundError` so the
  registry's error map produces the stable ``code="ConnectionNotFoundError"``
  wire shape used by :func:`mcp.tools.connections.connect`.
* ``SetInfo`` and ``ClusterNode`` are pydantic models (not NamedTuples), so
  serialisation goes through ``model_dump()`` — same pattern as B.1.
* Tools are registered with ``mutation=False``; they are absent from
  :data:`access_profile.WRITE_TOOLS`, so the read-only profile permits them.
* The ``@tool`` decorator already wraps every body in the access-profile
  gate and ``map_aerospike_errors`` — do **not** apply them again here.
"""

from __future__ import annotations

from typing import Any

from aerospike_cluster_manager_api.client_manager import client_manager
from aerospike_cluster_manager_api.mcp.registry import tool
from aerospike_cluster_manager_api.services import clusters_service
from aerospike_cluster_manager_api.services.connections_service import (
    ConnectionNotFoundError,
)


async def _get_client(conn_id: str) -> Any:
    """Resolve a live ``AsyncClient`` for ``conn_id``.

    ``client_manager.get_client`` raises :class:`ValueError` when the profile
    is unknown. We translate that into :class:`ConnectionNotFoundError` so
    the registry's error map produces the canonical
    ``code="ConnectionNotFoundError"`` wire shape — matching
    :func:`mcp.tools.connections.connect`.
    """
    try:
        return await client_manager.get_client(conn_id)
    except ValueError as e:
        raise ConnectionNotFoundError(conn_id) from e


@tool(category="cluster_info", mutation=False)
async def list_namespaces(conn_id: str) -> list[str]:
    """List all namespaces defined on the connected Aerospike cluster."""
    client = await _get_client(conn_id)
    return await clusters_service.list_namespaces(client)


@tool(category="cluster_info", mutation=False)
async def list_sets(conn_id: str, namespace: str) -> list[dict[str, Any]]:
    """List sets within a namespace, with object counts and byte sizes.

    Returns a list of ``SetInfo`` dicts (``name``, ``namespace``,
    ``objects``, ``tombstones``, ``memoryDataBytes``, ``stopWritesCount``,
    ``nodeCount``, ``totalNodes``). Raises ``MCPToolError`` with
    ``code="NamespaceNotFoundError"`` when the namespace is unknown.
    """
    client = await _get_client(conn_id)
    sets = await clusters_service.list_sets(client, namespace)
    return [s.model_dump() for s in sets]


@tool(category="cluster_info", mutation=False)
async def get_nodes(conn_id: str) -> list[dict[str, Any]]:
    """List nodes in the cluster with build/edition/uptime/connection metadata.

    Returns a list of ``ClusterNode`` dicts (``name``, ``address``, ``port``,
    ``build``, ``edition``, ``clusterSize``, ``uptime``, ``clientConnections``,
    ``statistics``).
    """
    client = await _get_client(conn_id)
    nodes = await clusters_service.get_nodes(client, conn_id)
    return [n.model_dump() for n in nodes]

"""MCP info command tools.

* ``execute_info`` / ``execute_info_on_node`` — full asinfo surface,
  classified as **mutation** because asinfo can change cluster config
  (``set-config``, ``recluster``, ``truncate-namespace``).
* ``execute_info_read_only`` — single-verb diagnostic reads, callable
  under ``ACM_MCP_ACCESS_PROFILE=read_only``. The verb whitelist lives
  in :mod:`info_verbs`; rejected verbs surface as
  ``code=invalid_argument``.
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

    WARNING: This tool is gated by ``ACM_MCP_ACCESS_PROFILE`` since some
    asinfo commands write (``set-config``, ``recluster``,
    ``truncate-namespace``). Under ``READ_ONLY`` profile this tool returns
    ``code=access_denied`` for ALL commands — including read-only ones —
    because the access gate operates on tool name, not command content.
    For diagnostic reads under READ_ONLY, use ``execute_info_read_only``
    (whitelisted verbs only) or the dedicated ``list_namespaces`` /
    ``list_sets`` / ``get_nodes`` tools.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    results = await clusters_service.execute_info(client, command)
    return {"nodes": [{"node": r.node_name, "error_code": r.error_code, "response": r.response} for r in results]}


@tool(category="info", mutation=True)
async def execute_info_on_node(conn_id: str, command: str, node_name: str) -> dict[str, str]:
    """Run an asinfo command on a single node and return the response.

    WARNING: This tool is gated by ``ACM_MCP_ACCESS_PROFILE`` since some
    asinfo commands write (``set-config``, ``recluster``,
    ``truncate-namespace``). Under ``READ_ONLY`` profile this tool returns
    ``code=access_denied`` for ALL commands — including read-only ones —
    because the access gate operates on tool name, not command content.
    For per-node diagnostic reads under READ_ONLY, use
    ``execute_info_read_only(command, node_name=...)``.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    response = await clusters_service.execute_info_on_node(client, command, node_name)
    return {"node": node_name, "response": response}


@tool(category="info", mutation=False)
async def execute_info_read_only(
    conn_id: str,
    command: str,
    node_name: str | None = None,
) -> dict[str, str]:
    """Run a whitelisted read-only asinfo command — callable under READ_ONLY profile.

    The leading verb is checked against an explicit allowlist
    (:data:`info_verbs.READ_ONLY_INFO_VERBS` — 24 verbs covering cluster
    metadata, topology, namespace introspection, statistics/latency, and
    strong-consistency/rack reads). Verbs outside the allowlist (writes,
    debug dumps, unknown verbs, XDR commands not available on CE) return
    ``code=invalid_argument`` along with a hint listing high-signal
    diagnostic verbs.

    Common reads exposed via this tool: ``namespaces``, ``version``,
    ``nodes``, ``statistics``, ``latencies``, ``roster:namespace=<ns>``,
    ``racks:``, ``sets``, ``sindex``, ``namespace/<ns>``,
    ``health-outliers``, ``health-stats``.

    With ``node_name=None`` (default) the call fans out via ``info_all``
    and returns the first non-error response — the ``node`` field of the
    result is the real cluster node (so a follow-up call can target it).
    With an explicit ``node_name`` the same fan-out is filtered to that
    node; ``NodeNotFoundError`` (mapped to a stable error code) surfaces
    when the node doesn't respond.

    Empty-string ``node_name`` is treated as "no node" (same as
    ``node_name=None``) so JSON callers that pass ``""`` for unset fields
    don't trigger a confusing ``NodeNotFoundError("")``.

    Returns ``{"node": str, "response": str}``.
    """
    client = await _get_client(conn_id)
    # Coerce the empty-string sentinel that some JSON callers use for
    # "field not set" — without this, the service would fan out and look
    # for a node literally named ``""``.
    effective_node = node_name or None
    node, response = await clusters_service.execute_info_read_only(client, command, effective_node)
    return {"node": node, "response": response}

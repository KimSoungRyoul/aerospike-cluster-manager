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
    (:mod:`info_verbs.READ_ONLY_INFO_VERBS`); commands whose verb is not
    on the list (writes, debug dumps, unknown verbs) return
    ``code=invalid_argument``. Currently allowed verbs:
    ``namespaces``, ``namespace``, ``sets``, ``bins``, ``sindex``,
    ``version``, ``build``, ``build-os``, ``build-time``, ``node``,
    ``service``, ``services``, ``services-alumni``, ``nodes``,
    ``cluster-name``, ``cluster-stable``, ``cluster-generation``,
    ``cluster-info``, ``health-outliers``, ``health-stats``,
    ``statistics``, ``latencies``, ``udf-list``, ``roster``, ``racks``,
    ``xdr-dc``, ``dc``.

    With ``node_name=None`` (default) the command runs on a random node
    via ``info_random_node`` — fine for cluster-uniform reads such as
    ``namespaces`` or ``version``. With an explicit ``node_name`` it fans
    out via ``info_all`` and filters; raises ``NodeNotFoundError`` if the
    node didn't respond.

    Returns ``{"node": str, "response": str}``. The ``node`` value is
    ``"<random>"`` when ``node_name`` was omitted.
    """
    client = await _get_client(conn_id)
    node, response = await clusters_service.execute_info_read_only(client, command, node_name)
    return {"node": node, "response": response}

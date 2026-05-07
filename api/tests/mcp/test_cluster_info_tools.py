"""Tests for the MCP cluster info tools (Task B.2).

These tests exercise the 3 cluster-info tools directly (bypassing the
FastMCP transport) — direct callable invocation is sufficient to verify
serialisation, error mapping, and the access-profile gate, all of which are
applied by the registry decorator.

Coverage matrix:

* every tool: happy path returns JSON-serialisable shape that mirrors the
  underlying service-layer response (``list[str]`` for namespaces, lists of
  dicts for sets/nodes — the underlying ``SetInfo`` / ``ClusterNode``
  pydantic models are ``model_dump()``-ed at the MCP boundary);
* error mapping: an unknown ``conn_id`` causes ``client_manager.get_client``
  to raise ``ValueError``; the tool re-raises as ``ConnectionNotFoundError``
  so the registry's error map produces ``code="ConnectionNotFoundError"``,
  matching the wire shape used by the B.1 ``connect`` tool;
* one verification that *importing* the module registers exactly 3 tools
  under ``category="cluster_info"`` so the auto-discovery wiring done in B.6
  sees the expected surface.

The 3 cluster-info tools are not in :data:`access_profile.WRITE_TOOLS`, so
the read-only profile is fine for all of them — there's no separate
read-only test, just the standard happy paths.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from aerospike_cluster_manager_api.mcp.errors import MCPToolError
from aerospike_cluster_manager_api.mcp.registry import registered_tools
from aerospike_cluster_manager_api.models.cluster import ClusterNode, SetInfo

# ---------------------------------------------------------------------------
# Module import side-effect: the 3 tools register themselves at import time
# so auto-discovery (B.6) sees them.
# ---------------------------------------------------------------------------


def test_cluster_info_tools_module_registers_three_tools() -> None:
    # Importing the module is enough — the @tool decorations run at import time.
    from aerospike_cluster_manager_api.mcp.tools import cluster_info as _cluster_info  # noqa: F401

    names = {entry.name for entry in registered_tools() if entry.category == "cluster_info"}
    assert names == {"list_namespaces", "list_sets", "get_nodes"}


def test_mutation_flags_are_all_false() -> None:
    from aerospike_cluster_manager_api.mcp.tools import cluster_info as _cluster_info  # noqa: F401

    by_name = {entry.name: entry for entry in registered_tools() if entry.category == "cluster_info"}
    # All 3 tools are read-only.
    assert by_name["list_namespaces"].mutation is False
    assert by_name["list_sets"].mutation is False
    assert by_name["get_nodes"].mutation is False


# ---------------------------------------------------------------------------
# list_namespaces
# ---------------------------------------------------------------------------


class TestListNamespaces:
    async def test_happy_path_returns_list_of_strings(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import list_namespaces

        mock_client = MagicMock()
        mock_client.info_random_node = AsyncMock(return_value="test;bar")

        with patch.object(
            ci_tools.client_manager,
            "get_client",
            new=AsyncMock(return_value=mock_client),
        ):
            result = await list_namespaces(conn_id="conn-x")

        assert isinstance(result, list)
        assert result == ["test", "bar"]
        assert all(isinstance(ns, str) for ns in result)

    async def test_returns_empty_list_when_no_namespaces(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import list_namespaces

        mock_client = MagicMock()
        mock_client.info_random_node = AsyncMock(return_value="")

        with patch.object(
            ci_tools.client_manager,
            "get_client",
            new=AsyncMock(return_value=mock_client),
        ):
            result = await list_namespaces(conn_id="conn-x")

        assert result == []

    async def test_missing_conn_id_maps_to_mcp_error(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import list_namespaces

        # client_manager.get_client raises ValueError for unknown profiles.
        # The tool must re-raise as ConnectionNotFoundError so the registry's
        # error map produces a stable wire code matching the connect tool.
        with (
            patch.object(
                ci_tools.client_manager,
                "get_client",
                new=AsyncMock(side_effect=ValueError("Connection profile 'conn-nope' not found")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await list_namespaces(conn_id="conn-nope")
        assert exc_info.value.code == "ConnectionNotFoundError"


# ---------------------------------------------------------------------------
# list_sets
# ---------------------------------------------------------------------------


def _make_mock_client_for_sets() -> AsyncMock:
    """Build a mock AsyncClient that returns realistic per-set info data."""
    mock = AsyncMock()
    mock.get_node_names = Mock(return_value=["node1", "node2"])

    # info_random_node is used by list_namespaces (which is called by list_sets
    # for the existence check) — return the namespace list.
    mock.info_random_node = AsyncMock(return_value="test")

    def info_all_side_effect(cmd: str):
        if cmd.startswith("namespace/"):
            ns_stats = "objects=200;replication-factor=2"
            return [("node1", None, ns_stats), ("node2", None, ns_stats)]
        if cmd.startswith("sets/"):
            sets_resp = "set=myset:objects=100:tombstones=0:memory_data_bytes=500:stop-writes-count=0"
            return [("node1", None, sets_resp), ("node2", None, sets_resp)]
        return []

    mock.info_all = AsyncMock(side_effect=info_all_side_effect)
    return mock


class TestListSets:
    async def test_happy_path_returns_list_of_dicts(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import list_sets

        mock_client = _make_mock_client_for_sets()

        with patch.object(
            ci_tools.client_manager,
            "get_client",
            new=AsyncMock(return_value=mock_client),
        ):
            result = await list_sets(conn_id="conn-x", namespace="test")

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        assert len(result) == 1
        item = result[0]
        # Must mirror the SetInfo pydantic model exactly.
        assert item["name"] == "myset"
        assert item["namespace"] == "test"
        assert "objects" in item
        assert "tombstones" in item
        assert "memoryDataBytes" in item
        assert "stopWritesCount" in item
        assert "nodeCount" in item
        assert "totalNodes" in item
        # And that it round-trips through the pydantic model — proves the
        # shape matches the wire contract used by the REST router.
        SetInfo(**item)

    async def test_unknown_namespace_maps_to_mcp_error(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import list_sets

        mock_client = _make_mock_client_for_sets()
        # No matching namespace — list_namespaces returns [] so the existence
        # check in clusters_service.list_sets raises NamespaceNotFoundError,
        # which the registry's error map translates to MCPToolError.
        mock_client.info_random_node = AsyncMock(return_value="")

        with (
            patch.object(
                ci_tools.client_manager,
                "get_client",
                new=AsyncMock(return_value=mock_client),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await list_sets(conn_id="conn-x", namespace="missing")
        assert exc_info.value.code == "NamespaceNotFoundError"

    async def test_missing_conn_id_maps_to_mcp_error(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import list_sets

        with (
            patch.object(
                ci_tools.client_manager,
                "get_client",
                new=AsyncMock(side_effect=ValueError("Connection profile 'conn-nope' not found")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await list_sets(conn_id="conn-nope", namespace="test")
        assert exc_info.value.code == "ConnectionNotFoundError"


# ---------------------------------------------------------------------------
# get_nodes
# ---------------------------------------------------------------------------


def _make_mock_client_for_nodes() -> AsyncMock:
    """Build a mock AsyncClient that returns realistic per-node info data."""
    mock = AsyncMock()
    mock.get_node_names = Mock(return_value=["node1", "node2"])

    node_stats = "cluster_size=2;uptime=3600;client_connections=10"

    def info_all_side_effect(cmd: str):
        if cmd == "statistics":
            return [("node1", None, node_stats), ("node2", None, node_stats)]
        if cmd == "build":
            return [("node1", None, "8.1.0"), ("node2", None, "8.1.0")]
        if cmd == "edition":
            return [("node1", None, "Community"), ("node2", None, "Community")]
        if cmd == "service":
            return [("node1", None, "10.0.0.1:3000"), ("node2", None, "10.0.0.2:3000")]
        return []

    mock.info_all = AsyncMock(side_effect=info_all_side_effect)
    return mock


class TestGetNodes:
    async def test_happy_path_returns_list_of_dicts(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import get_nodes
        from aerospike_cluster_manager_api.services.info_cache import info_cache

        info_cache.clear()
        mock_client = _make_mock_client_for_nodes()

        with patch.object(
            ci_tools.client_manager,
            "get_client",
            new=AsyncMock(return_value=mock_client),
        ):
            result = await get_nodes(conn_id="conn-test-1")

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        assert len(result) == 2
        # Inspect one node's payload — must mirror ClusterNode schema.
        item = result[0]
        assert item["name"] in {"node1", "node2"}
        assert item["build"] == "8.1.0"
        assert item["edition"] == "Community"
        assert "address" in item
        assert "port" in item
        assert "clusterSize" in item
        assert "uptime" in item
        assert "clientConnections" in item
        assert "statistics" in item
        # Round-trip through the pydantic model — proves the shape matches
        # the wire contract used by the REST router.
        ClusterNode(**item)
        info_cache.clear()

    async def test_missing_conn_id_maps_to_mcp_error(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import cluster_info as ci_tools
        from aerospike_cluster_manager_api.mcp.tools.cluster_info import get_nodes

        with (
            patch.object(
                ci_tools.client_manager,
                "get_client",
                new=AsyncMock(side_effect=ValueError("Connection profile 'conn-nope' not found")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await get_nodes(conn_id="conn-nope")
        assert exc_info.value.code == "ConnectionNotFoundError"

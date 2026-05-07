"""Tests for the MCP connection tools (Task B.1).

These tests exercise each of the 8 connection tools directly (bypassing the
FastMCP transport) — direct callable invocation is sufficient to verify
serialisation, error mapping, and the access-profile gate, all of which are
applied by the registry decorator.

Coverage matrix:

* every tool: happy path returns JSON-serialisable shape that mirrors the
  underlying service-layer response;
* mutation tools (``create_connection``, ``update_connection``,
  ``delete_connection``): under the ``READ_ONLY`` profile, the call raises
  ``MCPToolError(code="access_denied")`` *before* the body runs;
* error mapping: deleting a missing connection (and adjacent paths) surfaces
  a stable ``MCPToolError`` with the service-layer exception name as
  ``code``;
* one verification that *importing* the module registers exactly 8 tools so
  the auto-discovery wiring done in B.6 sees the expected surface.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aerospike_cluster_manager_api import config
from aerospike_cluster_manager_api.mcp.access_profile import AccessProfile
from aerospike_cluster_manager_api.mcp.errors import MCPToolError
from aerospike_cluster_manager_api.mcp.registry import (
    _reset_for_tests,
    registered_tools,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the access profile to FULL so mutation tools are not blocked."""
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.FULL)


@pytest.fixture
def read_only_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the access profile to READ_ONLY."""
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.READ_ONLY)


# ---------------------------------------------------------------------------
# Module import side-effect: the 8 tools register themselves at import time
# so auto-discovery (B.6) sees them. This single test asserts the count and
# the categories without resetting the registry — every other test below
# imports tool callables directly and reasons about them via direct invoke.
# ---------------------------------------------------------------------------


def test_connection_tools_module_registers_eight_tools() -> None:
    # Importing the module is enough — the @tool decorations run at import time.
    from aerospike_cluster_manager_api.mcp.tools import connections as _connections  # noqa: F401

    names = {entry.name for entry in registered_tools() if entry.category == "connection"}
    assert names == {
        "create_connection",
        "get_connection",
        "update_connection",
        "delete_connection",
        "list_connections",
        "connect",
        "disconnect",
        "test_connection",
    }


def test_mutation_flags_match_design() -> None:
    from aerospike_cluster_manager_api.mcp.tools import connections as _connections  # noqa: F401

    by_name = {entry.name: entry for entry in registered_tools() if entry.category == "connection"}
    assert by_name["create_connection"].mutation is True
    assert by_name["update_connection"].mutation is True
    assert by_name["delete_connection"].mutation is True
    # Read tools (and the connect/disconnect pair, which we treat as
    # non-mutation) must not advertise mutation.
    assert by_name["get_connection"].mutation is False
    assert by_name["list_connections"].mutation is False
    assert by_name["connect"].mutation is False
    assert by_name["disconnect"].mutation is False
    assert by_name["test_connection"].mutation is False


# ---------------------------------------------------------------------------
# create_connection
# ---------------------------------------------------------------------------


class TestCreateConnection:
    async def test_happy_path_returns_serialisable_dict(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import create_connection

        result = await create_connection(
            name="MCP Test",
            hosts=["10.0.0.1"],
            port=3000,
            color="#FF5500",
        )
        assert isinstance(result, dict)
        assert result["name"] == "MCP Test"
        assert result["hosts"] == ["10.0.0.1"]
        assert result["port"] == 3000
        assert result["color"] == "#FF5500"
        # workspaceId falls back to the built-in default.
        assert result["workspaceId"] == "ws-default"
        # Password must never leak through.
        assert "password" not in result

    async def test_read_only_profile_blocks_call(self, init_test_db, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import create_connection

        with pytest.raises(MCPToolError) as exc_info:
            await create_connection(name="MCP Test", hosts=["10.0.0.1"])

        assert exc_info.value.code == "access_denied"
        assert "create_connection" in str(exc_info.value)

    async def test_cluster_name_passed_through(self, init_test_db, full_profile: None) -> None:
        """Phase 1: ``cluster_name`` parameter is forwarded as
        ``clusterName=...`` on the underlying ``CreateConnectionRequest`` so
        the Aerospike client tend (cluster-name policy) sees the operator's
        chosen identifier.
        """
        from aerospike_cluster_manager_api.mcp.tools.connections import create_connection

        result = await create_connection(
            name="With Cluster Name",
            hosts=["10.0.0.1"],
            cluster_name="prod-cluster-east",
        )
        assert isinstance(result, dict)
        assert result["clusterName"] == "prod-cluster-east"


# ---------------------------------------------------------------------------
# get_connection
# ---------------------------------------------------------------------------


class TestGetConnection:
    async def test_happy_path_returns_dict(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import (
            create_connection,
            get_connection,
        )

        created = await create_connection(name="Lookup Me", hosts=["1.1.1.1"])
        result = await get_connection(conn_id=created["id"])
        assert isinstance(result, dict)
        assert result["id"] == created["id"]
        assert result["name"] == "Lookup Me"

    async def test_missing_id_maps_to_mcp_error(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import get_connection

        with pytest.raises(MCPToolError) as exc_info:
            await get_connection(conn_id="conn-nonexistent")
        assert exc_info.value.code == "ConnectionNotFoundError"


# ---------------------------------------------------------------------------
# update_connection
# ---------------------------------------------------------------------------


class TestUpdateConnection:
    async def test_happy_path_returns_updated_dict(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import (
            create_connection,
            update_connection,
        )

        created = await create_connection(name="Old Name", hosts=["10.0.0.1"])
        result = await update_connection(conn_id=created["id"], name="New Name", port=4000)
        assert isinstance(result, dict)
        assert result["name"] == "New Name"
        assert result["port"] == 4000
        # Untouched fields preserved.
        assert result["hosts"] == ["10.0.0.1"]

    async def test_read_only_profile_blocks_call(self, init_test_db, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import update_connection

        with pytest.raises(MCPToolError) as exc_info:
            await update_connection(conn_id="conn-x", name="Y")
        assert exc_info.value.code == "access_denied"

    async def test_missing_id_maps_to_mcp_error(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import update_connection

        with pytest.raises(MCPToolError) as exc_info:
            await update_connection(conn_id="conn-nonexistent", name="X")
        assert exc_info.value.code == "ConnectionNotFoundError"

    async def test_cluster_name_passed_through(self, init_test_db, full_profile: None) -> None:
        """Phase 1: ``cluster_name`` parameter on ``update_connection`` is
        forwarded as ``clusterName=...`` so an operator can change the
        Aerospike cluster identifier (cluster-name tend policy) without
        creating a new profile."""
        from aerospike_cluster_manager_api.mcp.tools.connections import (
            create_connection,
            update_connection,
        )

        created = await create_connection(name="Will Update", hosts=["10.0.0.1"])
        result = await update_connection(
            conn_id=created["id"],
            cluster_name="renamed-cluster",
        )
        assert result["clusterName"] == "renamed-cluster"


# ---------------------------------------------------------------------------
# delete_connection
# ---------------------------------------------------------------------------


class TestDeleteConnection:
    async def test_happy_path_returns_none_or_status(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import (
            create_connection,
            delete_connection,
            get_connection,
        )

        created = await create_connection(name="Delete Me", hosts=["1.1.1.1"])
        result = await delete_connection(conn_id=created["id"])
        # The tool surface returns a small JSON-serialisable acknowledgement.
        assert isinstance(result, dict)
        assert result.get("deleted") is True
        # And the connection is in fact gone.
        with pytest.raises(MCPToolError):
            await get_connection(conn_id=created["id"])

    async def test_read_only_profile_blocks_call(self, init_test_db, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import delete_connection

        with pytest.raises(MCPToolError) as exc_info:
            await delete_connection(conn_id="conn-x")
        assert exc_info.value.code == "access_denied"

    async def test_idempotent_for_missing(self, init_test_db, full_profile: None) -> None:
        # Mirrors the service-layer contract: deleting a missing conn is a no-op.
        from aerospike_cluster_manager_api.mcp.tools.connections import delete_connection

        result = await delete_connection(conn_id="conn-nonexistent")
        assert isinstance(result, dict)
        assert result.get("deleted") is True


# ---------------------------------------------------------------------------
# list_connections
# ---------------------------------------------------------------------------


class TestListConnections:
    async def test_happy_path_returns_list_of_dicts(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import (
            create_connection,
            list_connections,
        )

        await create_connection(name="A", hosts=["1.1.1.1"])
        await create_connection(name="B", hosts=["2.2.2.2"])

        result = await list_connections()
        assert isinstance(result, list)
        assert len(result) >= 2
        assert all(isinstance(item, dict) for item in result)
        names = {item["name"] for item in result}
        assert {"A", "B"}.issubset(names)

    async def test_workspace_filter(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import list_connections

        result = await list_connections(workspace_id="ws-default")
        assert isinstance(result, list)
        assert all(item["workspaceId"] == "ws-default" for item in result)

    async def test_unknown_workspace_maps_to_mcp_error(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import list_connections

        with pytest.raises(MCPToolError) as exc_info:
            await list_connections(workspace_id="ws-missing")
        assert exc_info.value.code == "WorkspaceNotFoundError"


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    async def test_connect_returns_status_dict(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools import connections as conn_tools
        from aerospike_cluster_manager_api.mcp.tools.connections import (
            connect,
            create_connection,
        )

        created = await create_connection(name="Live", hosts=["10.0.0.1"])

        mock_client = MagicMock()
        mock_client.get_node_names = MagicMock(return_value=["node-1", "node-2"])
        mock_client.info_random_node = AsyncMock(return_value="test;bar")

        with patch.object(
            conn_tools.client_manager,
            "get_client",
            new=AsyncMock(return_value=mock_client),
        ):
            result = await connect(conn_id=created["id"])

        assert isinstance(result, dict)
        assert result["connected"] is True
        assert result["node_count"] == 2
        assert result["namespaces"] == ["test", "bar"]

    async def test_connect_unknown_id_maps_to_mcp_error(self, init_test_db, full_profile: None) -> None:
        # client_manager.get_client raises ValueError when the profile is
        # missing — that path is not in the standard error map (it uses the
        # service-layer ConnectionNotFoundError instead). The connect tool
        # therefore surfaces it via ConnectionNotFoundError to keep the wire
        # shape consistent with get_connection.
        from aerospike_cluster_manager_api.mcp.tools.connections import connect

        with pytest.raises(MCPToolError) as exc_info:
            await connect(conn_id="conn-nonexistent")
        assert exc_info.value.code == "ConnectionNotFoundError"

    async def test_disconnect_returns_status_dict(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools import connections as conn_tools
        from aerospike_cluster_manager_api.mcp.tools.connections import disconnect

        with patch.object(
            conn_tools.client_manager,
            "close_client",
            new=AsyncMock(return_value=None),
        ) as mock_close:
            result = await disconnect(conn_id="conn-anything")

        assert isinstance(result, dict)
        assert result["disconnected"] is True
        mock_close.assert_awaited_once_with("conn-anything")


# ---------------------------------------------------------------------------
# test_connection (probe — does not persist)
# ---------------------------------------------------------------------------


class TestTestConnectionTool:
    async def test_happy_path_returns_dict_from_service(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import test_connection
        from aerospike_cluster_manager_api.services.connections_service import (
            # Aliased so pytest does not try to collect this NamedTuple as a
            # test class.
            TestConnectionResult as _TCResult,
        )

        async def _fake(req: Any) -> _TCResult:
            assert req.hosts == ["10.0.0.1"]
            assert req.port == 3000
            # Phase 1: service returns a NamedTuple, not a dict.
            return _TCResult(success=True, message="Connected successfully")

        with patch(
            "aerospike_cluster_manager_api.mcp.tools.connections.connections_service.test_connection",
            side_effect=_fake,
        ):
            result = await test_connection(hosts=["10.0.0.1"], port=3000)

        # The MCP tool wraps the service result back into a JSON-serialisable
        # dict for transport.
        assert result == {"success": True, "message": "Connected successfully"}

    async def test_passes_credentials(self, init_test_db, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.connections import test_connection
        from aerospike_cluster_manager_api.services.connections_service import (
            TestConnectionResult as _TCResult,
        )

        captured: dict[str, Any] = {}

        async def _fake(req: Any) -> _TCResult:
            captured["user"] = req.username
            captured["pass"] = req.password
            return _TCResult(success=True, message="ok")

        with patch(
            "aerospike_cluster_manager_api.mcp.tools.connections.connections_service.test_connection",
            side_effect=_fake,
        ):
            await test_connection(hosts=["localhost"], port=3000, username="admin", password="secret")

        assert captured == {"user": "admin", "pass": "secret"}


# ---------------------------------------------------------------------------
# Registry isolation marker — the module-level @tool decorations must not
# leak across the boundary of this test file. The registry test file uses
# _reset_for_tests autouse fixture; we intentionally leave the connection
# tools registered here so other suites that introspect them still see the
# count.
# ---------------------------------------------------------------------------


def test_reset_for_tests_helper_clears_connection_tools() -> None:
    # Importing the tools module first ensures the decorator side-effects ran.
    from aerospike_cluster_manager_api.mcp import registry as _registry
    from aerospike_cluster_manager_api.mcp.tools import connections as _connections  # noqa: F401

    assert any(entry.category == "connection" for entry in registered_tools())
    saved = list(_registry._REGISTRY)
    try:
        _reset_for_tests()
        assert registered_tools() == []
    finally:
        # Restore the full snapshot — reloading just the connections module
        # would only repopulate the 8 connection tools because the other tool
        # modules are already imported (cached) and their decorators do not
        # re-run. Snapshot/restore is symmetrical and order-independent.
        _registry._REGISTRY[:] = saved
    assert any(entry.category == "connection" for entry in registered_tools())

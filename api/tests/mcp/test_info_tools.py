"""Tests for the MCP info command tools (Task B.5)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aerospike_cluster_manager_api import config
from aerospike_cluster_manager_api.mcp.access_profile import AccessProfile
from aerospike_cluster_manager_api.mcp.errors import MCPToolError
from aerospike_cluster_manager_api.mcp.registry import registered_tools


@pytest.fixture
def full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.FULL)


@pytest.fixture
def read_only_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.READ_ONLY)


def _patch_get_client(client: MagicMock):
    from aerospike_cluster_manager_api.mcp.tools import info_commands

    return patch.object(info_commands.client_manager, "get_client", new=AsyncMock(return_value=client))


def test_info_tools_module_registers_two_tools() -> None:
    from aerospike_cluster_manager_api.mcp.tools import info_commands as _ic  # noqa: F401

    names = {e.name for e in registered_tools() if e.category == "info"}
    assert names == {"execute_info", "execute_info_on_node"}
    by_name = {e.name: e for e in registered_tools() if e.category == "info"}
    assert by_name["execute_info"].mutation is True
    assert by_name["execute_info_on_node"].mutation is True


class TestExecuteInfo:
    async def test_happy_path(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info

        results = [
            SimpleNamespace(node_name="BB9", error_code=None, response="version 8.1"),
            SimpleNamespace(node_name="CC1", error_code=None, response="version 8.1"),
        ]
        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.info_commands.clusters_service.execute_info",
                new=AsyncMock(return_value=results),
            ),
        ):
            out = await execute_info(conn_id="conn-x", command="version")

        assert len(out["nodes"]) == 2
        assert out["nodes"][0] == {"node": "BB9", "error_code": None, "response": "version 8.1"}

    async def test_read_only_blocks(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info

        with pytest.raises(MCPToolError) as exc_info:
            await execute_info(conn_id="conn-x", command="version")
        assert exc_info.value.code == "access_denied"


class TestExecuteInfoOnNode:
    async def test_happy_path(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_on_node

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.info_commands.clusters_service.execute_info_on_node",
                new=AsyncMock(return_value="version 8.1"),
            ),
        ):
            out = await execute_info_on_node(conn_id="conn-x", command="version", node_name="BB9")

        assert out == {"node": "BB9", "response": "version 8.1"}

    async def test_read_only_blocks(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_on_node

        with pytest.raises(MCPToolError) as exc_info:
            await execute_info_on_node(conn_id="conn-x", command="version", node_name="BB9")
        assert exc_info.value.code == "access_denied"

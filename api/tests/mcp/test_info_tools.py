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
    """Backwards-compat shim — delegates to the package-level helper in
    :mod:`tests.mcp.conftest` so the duplicated boilerplate has a single
    source of truth."""
    from .conftest import patch_mcp_client

    return patch_mcp_client("aerospike_cluster_manager_api.mcp.tools.info_commands", client)


def test_info_tools_module_registers_three_tools() -> None:
    from aerospike_cluster_manager_api.mcp.tools import info_commands as _ic  # noqa: F401

    names = {e.name for e in registered_tools() if e.category == "info"}
    assert names == {"execute_info", "execute_info_on_node", "execute_info_read_only"}
    by_name = {e.name: e for e in registered_tools() if e.category == "info"}
    assert by_name["execute_info"].mutation is True
    assert by_name["execute_info_on_node"].mutation is True
    assert by_name["execute_info_read_only"].mutation is False


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


class TestExecuteInfoReadOnly:
    """MCP-tool-layer tests for the read-only asinfo entry point.

    These exercise the wrapper code path: client lookup, empty-string
    coercion for ``node_name``, service delegation, and end-to-end error
    code translation via the registry's ``map_aerospike_errors``.
    """

    async def test_random_node_happy_path(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_read_only

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.info_commands.clusters_service.execute_info_read_only",
                new=AsyncMock(return_value=("BB9", "test;bar")),
            ),
        ):
            out = await execute_info_read_only(conn_id="conn-x", command="namespaces")

        # Real cluster node name surfaces (no <random> sentinel).
        assert out == {"node": "BB9", "response": "test;bar"}

    async def test_specific_node(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_read_only

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.info_commands.clusters_service.execute_info_read_only",
                new=AsyncMock(return_value=("BB9", "8.1.0.0")),
            ),
        ):
            out = await execute_info_read_only(conn_id="conn-x", command="version", node_name="BB9")

        assert out == {"node": "BB9", "response": "8.1.0.0"}

    async def test_empty_string_node_coerces_to_none(self, read_only_profile: None) -> None:
        # JSON callers that pass ``""`` for unset fields should get the
        # random-node behaviour, not a ``NodeNotFoundError("")``. The
        # tool layer coerces; the service layer must therefore receive
        # ``None``.
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_read_only

        mock_client = MagicMock()
        service_mock = AsyncMock(return_value=("BB9", "8.1.0.0"))
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.info_commands.clusters_service.execute_info_read_only",
                new=service_mock,
            ),
        ):
            await execute_info_read_only(conn_id="conn-x", command="version", node_name="")

        # 3rd positional arg to the service is ``node_name`` — must be None.
        service_mock.assert_awaited_once()
        _, args, _ = service_mock.mock_calls[0]
        # Service is called as ``execute_info_read_only(client, command, effective_node)``
        assert args[2] is None

    async def test_unwhitelisted_verb_blocked_via_invalid_argument(self, read_only_profile: None) -> None:
        # The whitelist check fires inside the service, raises
        # InfoVerbNotAllowed, which the MCP error map translates to
        # ``invalid_argument``. From the tool's perspective we should see
        # MCPToolError(code="invalid_argument") — NOT access_denied (the
        # tool itself is read-only-callable; the *verb* is invalid).
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_read_only

        mock_client = MagicMock()
        # We don't patch the service here — the real
        # clusters_service.execute_info_read_only runs and the verb
        # check fires before any client call.
        with _patch_get_client(mock_client), pytest.raises(MCPToolError) as exc_info:
            await execute_info_read_only(conn_id="conn-x", command="set-config:context=service;migrate-threads=2")

        assert exc_info.value.code == "invalid_argument"
        assert "set-config" in str(exc_info.value)

    async def test_whitelist_still_applies_under_full(self, full_profile: None) -> None:
        # The whitelist is part of the tool's contract, NOT just a
        # READ_ONLY-profile gate — under FULL, a write verb on the
        # read-only tool must still be rejected with invalid_argument
        # (the tool is read-only by design; FULL just means access-denied
        # gates don't fire). Service is NOT mocked so the real whitelist
        # gate executes.
        from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info_read_only

        mock_client = MagicMock()
        with _patch_get_client(mock_client), pytest.raises(MCPToolError) as exc_info:
            await execute_info_read_only(conn_id="conn-x", command="recluster:")

        assert exc_info.value.code == "invalid_argument"
        # Critical: the wire was NOT touched even under FULL.
        mock_client.info_all.assert_not_called()
        mock_client.info_random_node.assert_not_called()

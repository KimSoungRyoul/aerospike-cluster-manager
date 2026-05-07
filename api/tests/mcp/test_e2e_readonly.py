"""Read-only profile end-to-end (Task C.2).

Verifies that ``ACM_MCP_ACCESS_PROFILE=read_only`` blocks mutation tools at
call time with the canonical access-denied error code, while read tools
continue to work. Mocks the underlying service layer so no Aerospike is
needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aerospike_cluster_manager_api import config
from aerospike_cluster_manager_api.mcp.access_profile import AccessProfile
from aerospike_cluster_manager_api.mcp.errors import MCPToolError


@pytest.fixture
def read_only_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.READ_ONLY)


@pytest.mark.parametrize(
    "tool_name,kwargs",
    [
        ("create_record", {"conn_id": "x", "namespace": "test", "set_name": "s", "key": "1", "bins": {"a": 1}}),
        ("update_record", {"conn_id": "x", "namespace": "test", "set_name": "s", "key": "1", "bins": {"a": 1}}),
        ("delete_record", {"conn_id": "x", "namespace": "test", "set_name": "s", "key": "1"}),
        ("delete_bin", {"conn_id": "x", "namespace": "test", "set_name": "s", "key": "1", "bin_name": "a"}),
        ("truncate_set", {"conn_id": "x", "namespace": "test", "set_name": "s"}),
    ],
)
async def test_record_mutation_tools_blocked_under_read_only(
    read_only_profile: None, tool_name: str, kwargs: dict
) -> None:
    from aerospike_cluster_manager_api.mcp.tools import records as records_tools

    fn = getattr(records_tools, tool_name)
    with pytest.raises(MCPToolError) as exc_info:
        await fn(**kwargs)
    assert exc_info.value.code == "access_denied"
    assert tool_name in str(exc_info.value)


async def test_execute_info_blocked_under_read_only(read_only_profile: None) -> None:
    from aerospike_cluster_manager_api.mcp.tools.info_commands import execute_info

    with pytest.raises(MCPToolError) as exc_info:
        await execute_info(conn_id="x", command="version")
    assert exc_info.value.code == "access_denied"


async def test_read_tool_works_under_read_only(read_only_profile: None) -> None:
    """``get_record`` is mutation=False so READ_ONLY does not block it."""
    from types import SimpleNamespace

    from aerospike_cluster_manager_api.mcp.tools import records as records_tools

    fake_record = SimpleNamespace(
        key=("test", "s", "1", b"\x00"),
        meta=SimpleNamespace(gen=1, ttl=0),
        bins={"name": "Alice"},
    )
    with (
        patch.object(records_tools.client_manager, "get_client", new=AsyncMock(return_value=object())),
        patch(
            "aerospike_cluster_manager_api.mcp.tools.records.records_service.get_record",
            new=AsyncMock(return_value=fake_record),
        ),
    ):
        out = await records_tools.get_record(conn_id="x", namespace="test", set_name="s", key="1")

    assert out["key"]["namespace"] == "test"
    assert out["bins"]["name"] == "Alice"

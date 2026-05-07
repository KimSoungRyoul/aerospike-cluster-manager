"""Tests for the MCP record tools (Task B.3).

These tests exercise the 7 record-tool callables directly (bypassing the
FastMCP transport). Each tool wraps the corresponding service-layer
primitive in :mod:`aerospike_cluster_manager_api.services.records_service`,
which is mocked here so the tests stay hermetic — no Aerospike server, no
SQLite db, no live ``client_manager``.

Coverage matrix:

* every tool: happy path returns a JSON-serialisable shape that mirrors the
  agreed-upon ack / record envelope (see :mod:`mcp.serializers` for read
  shape, the per-tool docstring for write acks);
* mutation tools (``create_record``, ``update_record``, ``delete_record``,
  ``delete_bin``, ``truncate_set``): under the ``READ_ONLY`` profile, the
  call raises ``MCPToolError(code="access_denied")`` *before* the body
  runs;
* error mapping: missing ``conn_id`` surfaces ``ConnectionNotFoundError``;
  ``RecordExistsError`` surfaces ``record_exists``; ``RecordNotFound``
  surfaces ``record_not_found``;
* one verification that *importing* the module registers exactly 7 tools
  under ``category="record"`` so the auto-discovery wiring done in B.6
  sees the expected surface.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aerospike_py.exception import RecordExistsError, RecordNotFound

from aerospike_cluster_manager_api import config
from aerospike_cluster_manager_api.mcp.access_profile import AccessProfile
from aerospike_cluster_manager_api.mcp.errors import MCPToolError
from aerospike_cluster_manager_api.mcp.registry import registered_tools

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def full_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the access profile to FULL so mutation tools are not blocked."""
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.FULL)


@pytest.fixture
def read_only_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the access profile to READ_ONLY so mutation tools are blocked."""
    monkeypatch.setattr(config, "ACM_MCP_ACCESS_PROFILE", AccessProfile.READ_ONLY)


def _make_record(
    key=("test", "demo", "k1", b"\x00\x01"),
    meta=None,
    bins=None,
) -> SimpleNamespace:
    """Build a SimpleNamespace that mimics an aerospike-py Record NamedTuple."""
    return SimpleNamespace(
        key=key,
        meta=meta if meta is not None else SimpleNamespace(gen=1, ttl=0),
        bins=bins if bins is not None else {"name": "Alice"},
    )


def _patch_get_client(client: MagicMock):
    """Return a context manager that replaces ``_get_client`` with the mock.

    Backwards-compat shim — delegates to the package-level helper in
    :mod:`tests.mcp.conftest` so the duplicated boilerplate has a single
    source of truth.
    """
    from .conftest import patch_mcp_client

    return patch_mcp_client("aerospike_cluster_manager_api.mcp.tools.records", client)


# ---------------------------------------------------------------------------
# Module import side-effect: the 7 tools register themselves at import time
# ---------------------------------------------------------------------------


def test_record_tools_module_registers_seven_tools() -> None:
    # Importing the module is enough — the @tool decorations run at import.
    from aerospike_cluster_manager_api.mcp.tools import records as _records  # noqa: F401

    names = {entry.name for entry in registered_tools() if entry.category == "record"}
    assert names == {
        "get_record",
        "record_exists",
        "create_record",
        "update_record",
        "delete_record",
        "delete_bin",
        "truncate_set",
    }


def test_mutation_flags_match_design() -> None:
    from aerospike_cluster_manager_api.mcp.tools import records as _records  # noqa: F401

    by_name = {entry.name: entry for entry in registered_tools() if entry.category == "record"}
    # Read tools — mutation=False
    assert by_name["get_record"].mutation is False
    assert by_name["record_exists"].mutation is False
    # Mutation tools — mutation=True
    assert by_name["create_record"].mutation is True
    assert by_name["update_record"].mutation is True
    assert by_name["delete_record"].mutation is True
    assert by_name["delete_bin"].mutation is True
    assert by_name["truncate_set"].mutation is True


# ---------------------------------------------------------------------------
# get_record
# ---------------------------------------------------------------------------


class TestGetRecordTool:
    async def test_happy_path_returns_serialised_record(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import get_record

        rec = _make_record(
            key=("test", "demo", 42, b"\xab\xcd"),
            meta=SimpleNamespace(gen=7, ttl=3600),
            bins={"name": "Alice", "age": 30},
        )
        mock_client = MagicMock()

        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.get_record",
                new=AsyncMock(return_value=rec),
            ),
        ):
            result = await get_record(conn_id="conn-x", namespace="test", set_name="demo", key="42")

        assert isinstance(result, dict)
        # serialize_record envelope
        assert result["key"]["namespace"] == "test"
        assert result["key"]["set"] == "demo"
        assert result["key"]["user_key"] == 42
        assert result["meta"]["generation"] == 7
        assert result["meta"]["expiration"] == 3600
        assert result["bins"] == {"name": "Alice", "age": 30}

    async def test_missing_record_maps_to_record_not_found(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import get_record

        mock_client = MagicMock()

        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.get_record",
                new=AsyncMock(side_effect=RecordNotFound("nope")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await get_record(conn_id="conn-x", namespace="test", set_name="demo", key="missing")

        assert exc_info.value.code == "record_not_found"

    async def test_missing_conn_id_maps_to_connection_not_found(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import records as records_tools
        from aerospike_cluster_manager_api.mcp.tools.records import get_record

        with (
            patch.object(
                records_tools.client_manager,
                "get_client",
                new=AsyncMock(side_effect=ValueError("Connection profile 'conn-nope' not found")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await get_record(conn_id="conn-nope", namespace="test", set_name="demo", key="k1")

        assert exc_info.value.code == "ConnectionNotFoundError"


# ---------------------------------------------------------------------------
# record_exists
# ---------------------------------------------------------------------------


class TestRecordExistsTool:
    async def test_happy_path_true(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import record_exists

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.record_exists",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await record_exists(conn_id="conn-x", namespace="test", set_name="demo", key="k1")

        assert result == {"exists": True}

    async def test_happy_path_false(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import record_exists

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.record_exists",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await record_exists(conn_id="conn-x", namespace="test", set_name="demo", key="missing")

        assert result == {"exists": False}

    async def test_missing_conn_id_maps_to_connection_not_found(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import records as records_tools
        from aerospike_cluster_manager_api.mcp.tools.records import record_exists

        with (
            patch.object(
                records_tools.client_manager,
                "get_client",
                new=AsyncMock(side_effect=ValueError("missing")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await record_exists(conn_id="conn-nope", namespace="test", set_name="demo", key="k1")

        assert exc_info.value.code == "ConnectionNotFoundError"


# ---------------------------------------------------------------------------
# create_record
# ---------------------------------------------------------------------------


class TestCreateRecordTool:
    async def test_happy_path_returns_created_ack(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import create_record

        mock_client = MagicMock()
        spy = AsyncMock(return_value=None)
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.create_record",
                new=spy,
            ),
        ):
            result = await create_record(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bins={"name": "Alice"},
            )

        assert isinstance(result, dict)
        assert result["created"] is True
        assert result["key"]["namespace"] == "test"
        assert result["key"]["set"] == "demo"
        assert result["key"]["pk"] == "k1"
        spy.assert_awaited_once()

    async def test_record_exists_maps_to_record_exists(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import create_record

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.create_record",
                new=AsyncMock(side_effect=RecordExistsError("collision")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await create_record(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bins={"a": 1},
            )

        assert exc_info.value.code == "record_exists"

    async def test_read_only_profile_blocks_call(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import create_record

        with pytest.raises(MCPToolError) as exc_info:
            await create_record(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bins={"a": 1},
            )

        assert exc_info.value.code == "access_denied"
        assert "create_record" in str(exc_info.value)


# ---------------------------------------------------------------------------
# update_record
# ---------------------------------------------------------------------------


class TestUpdateRecordTool:
    async def test_happy_path_returns_updated_ack(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import update_record

        mock_client = MagicMock()
        spy = AsyncMock(return_value=None)
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.update_record",
                new=spy,
            ),
        ):
            result = await update_record(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bins={"name": "Bob"},
            )

        assert isinstance(result, dict)
        assert result["updated"] is True
        assert result["key"]["namespace"] == "test"
        assert result["key"]["set"] == "demo"
        assert result["key"]["pk"] == "k1"
        spy.assert_awaited_once()

    async def test_record_not_found_maps_to_record_not_found(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import update_record

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.update_record",
                new=AsyncMock(side_effect=RecordNotFound("absent")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await update_record(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="missing",
                bins={"a": 1},
            )

        assert exc_info.value.code == "record_not_found"

    async def test_read_only_profile_blocks_call(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import update_record

        with pytest.raises(MCPToolError) as exc_info:
            await update_record(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bins={"a": 1},
            )

        assert exc_info.value.code == "access_denied"


# ---------------------------------------------------------------------------
# delete_record
# ---------------------------------------------------------------------------


class TestDeleteRecordTool:
    async def test_happy_path_returns_deleted_ack(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import delete_record

        mock_client = MagicMock()
        spy = AsyncMock(return_value=None)
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.delete_record",
                new=spy,
            ),
        ):
            result = await delete_record(conn_id="conn-x", namespace="test", set_name="demo", key="k1")

        assert isinstance(result, dict)
        assert result["deleted"] is True
        assert result["key"]["pk"] == "k1"
        spy.assert_awaited_once()

    async def test_record_not_found_maps_to_record_not_found(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import delete_record

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.delete_record",
                new=AsyncMock(side_effect=RecordNotFound("absent")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await delete_record(conn_id="conn-x", namespace="test", set_name="demo", key="missing")

        assert exc_info.value.code == "record_not_found"

    async def test_read_only_profile_blocks_call(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import delete_record

        with pytest.raises(MCPToolError) as exc_info:
            await delete_record(conn_id="conn-x", namespace="test", set_name="demo", key="k1")

        assert exc_info.value.code == "access_denied"


# ---------------------------------------------------------------------------
# delete_bin
# ---------------------------------------------------------------------------


class TestDeleteBinTool:
    async def test_happy_path_returns_bin_deleted_ack(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import delete_bin

        mock_client = MagicMock()
        spy = AsyncMock(return_value=None)
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.delete_bin",
                new=spy,
            ),
        ):
            result = await delete_bin(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bin_name="old_bin",
            )

        assert isinstance(result, dict)
        assert result["bin_deleted"] is True
        assert result["bin"] == "old_bin"
        assert result["key"]["pk"] == "k1"
        spy.assert_awaited_once()

    async def test_record_not_found_maps_to_record_not_found(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import delete_bin

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.delete_bin",
                new=AsyncMock(side_effect=RecordNotFound("absent")),
            ),
            pytest.raises(MCPToolError) as exc_info,
        ):
            await delete_bin(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="missing",
                bin_name="old_bin",
            )

        assert exc_info.value.code == "record_not_found"

    async def test_read_only_profile_blocks_call(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import delete_bin

        with pytest.raises(MCPToolError) as exc_info:
            await delete_bin(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                key="k1",
                bin_name="old_bin",
            )

        assert exc_info.value.code == "access_denied"


# ---------------------------------------------------------------------------
# truncate_set
# ---------------------------------------------------------------------------


class TestTruncateSetTool:
    async def test_happy_path_returns_truncated_ack(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import truncate_set

        mock_client = MagicMock()
        spy = AsyncMock(return_value=None)
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.truncate_set",
                new=spy,
            ),
        ):
            result = await truncate_set(conn_id="conn-x", namespace="test", set_name="demo")

        assert isinstance(result, dict)
        assert result["truncated"] is True
        assert result["set"] == "demo"
        assert result["namespace"] == "test"
        spy.assert_awaited_once_with(mock_client, "test", "demo", before_lut=None)

    async def test_passes_before_lut(self, full_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import truncate_set

        mock_client = MagicMock()
        spy = AsyncMock(return_value=None)
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.truncate_set",
                new=spy,
            ),
        ):
            result = await truncate_set(
                conn_id="conn-x",
                namespace="test",
                set_name="demo",
                before_lut=1_700_000_000_000_000_000,
            )

        assert result["truncated"] is True
        spy.assert_awaited_once_with(mock_client, "test", "demo", before_lut=1_700_000_000_000_000_000)

    async def test_read_only_profile_blocks_call(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import truncate_set

        with pytest.raises(MCPToolError) as exc_info:
            await truncate_set(conn_id="conn-x", namespace="test", set_name="demo")

        assert exc_info.value.code == "access_denied"


# ---------------------------------------------------------------------------
# Module guarantees
# ---------------------------------------------------------------------------


class TestModuleHasNoFastAPI:
    def test_no_fastapi_import(self) -> None:
        import aerospike_cluster_manager_api.mcp.tools.records as mod

        assert "fastapi" not in mod.__dict__
        for attr in dir(mod):
            value = getattr(mod, attr, None)
            module_name = getattr(value, "__module__", "") or ""
            assert not module_name.startswith("fastapi"), f"{attr} originates in {module_name}"


# ---------------------------------------------------------------------------
# Defensive: non-mutation tools must NOT be access-gated even under READ_ONLY
# ---------------------------------------------------------------------------


class TestReadToolsNotGated:
    async def test_get_record_runs_under_read_only(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import get_record

        mock_client = MagicMock()
        rec = _make_record()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.get_record",
                new=AsyncMock(return_value=rec),
            ),
        ):
            result = await get_record(conn_id="conn-x", namespace="test", set_name="demo", key="k1")

        assert isinstance(result, dict)

    async def test_record_exists_runs_under_read_only(self, read_only_profile: None) -> None:
        from aerospike_cluster_manager_api.mcp.tools.records import record_exists

        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.records.records_service.record_exists",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await record_exists(conn_id="conn-x", namespace="test", set_name="demo", key="k1")

        assert result == {"exists": True}


# Silence unused-import warnings: the Mock class is imported to keep the
# fixture style aligned with sibling test files even when unused.
_ = Mock

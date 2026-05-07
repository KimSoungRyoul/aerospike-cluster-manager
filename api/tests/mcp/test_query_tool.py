"""Tests for the MCP query tool (Task B.4).

Coverage:
* module-level registration: exactly 1 tool under ``category="query"``,
  ``mutation=False``;
* happy path: scan returns serialised records + stats envelope;
* PK lookup branch: ``primary_key`` arg routes through to QueryRequest;
* predicate inline params: ``predicate_bin``+``predicate_operator``+
  ``predicate_value``[+``predicate_value2``] → ``QueryPredicate`` model;
* missing conn_id: ``ConnectionNotFoundError`` → ``MCPToolError``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from aerospike_cluster_manager_api.mcp.errors import MCPToolError
from aerospike_cluster_manager_api.mcp.registry import registered_tools

from .conftest import patch_mcp_client


def _make_record(
    key=("test", "sample_set", "k1", b"\x00\x01"),
    bins=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        meta=SimpleNamespace(gen=1, ttl=0),
        bins=bins if bins is not None else {"name": "Alice"},
    )


def _patch_get_client(client: MagicMock):
    """Backwards-compat shim — delegates to the package-level helper.

    Kept so the body of each test reads the same as the legacy form;
    the consolidated implementation lives in :mod:`tests.mcp.conftest`.
    """
    return patch_mcp_client("aerospike_cluster_manager_api.mcp.tools.query", client)


# ---------------------------------------------------------------------------
# Module-level registration
# ---------------------------------------------------------------------------


def test_query_tool_registers_one_entry() -> None:
    from aerospike_cluster_manager_api.mcp.tools import query as _query  # noqa: F401

    entries = [e for e in registered_tools() if e.category == "query"]
    assert len(entries) == 1
    assert entries[0].name == "query"
    assert entries[0].mutation is False


# ---------------------------------------------------------------------------
# Happy path: scan
# ---------------------------------------------------------------------------


class TestQueryTool:
    async def test_scan_returns_envelope(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.query import query

        result_obj = SimpleNamespace(
            records=[_make_record(), _make_record(key=("test", "sample_set", "k2", b"\xde\xad"))],
            execution_time_ms=12,
            scanned_records=2,
            returned_records=2,
        )
        mock_client = MagicMock()

        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.query.query_service.execute_query",
                new=AsyncMock(return_value=result_obj),
            ) as exec_mock,
        ):
            out = await query(
                conn_id="conn-x",
                namespace="test",
                set_name="sample_set",
                max_records=100,
            )

        assert out["execution_time_ms"] == 12
        assert out["scanned_records"] == 2
        assert out["returned_records"] == 2
        assert len(out["records"]) == 2
        # records were serialised — namespace+set+digest fields present.
        assert out["records"][0]["key"]["namespace"] == "test"
        # The body passed to execute_query was a QueryRequest with no primaryKey.
        assert exec_mock.await_args is not None
        body = exec_mock.await_args.args[1]
        assert body.namespace == "test"
        assert body.set == "sample_set"
        assert body.primaryKey is None
        assert body.predicate is None

    async def test_pk_lookup_routes_primary_key(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.query import query

        rec = _make_record(key=("test", "sample_set", 42, b"\xff"))
        result_obj = SimpleNamespace(records=[rec], execution_time_ms=1, scanned_records=1, returned_records=1)
        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.query.query_service.execute_query",
                new=AsyncMock(return_value=result_obj),
            ) as exec_mock,
        ):
            out = await query(
                conn_id="conn-x",
                namespace="test",
                set_name="sample_set",
                primary_key="42",
                pk_type="int",
            )

        assert out["returned_records"] == 1
        assert exec_mock.await_args is not None
        body = exec_mock.await_args.args[1]
        assert body.primaryKey == "42"
        assert body.pkType == "int"

    async def test_predicate_inline_params_are_coerced(self) -> None:
        """Phase 1: predicates are passed via four inline parameters
        (``predicate_bin``, ``predicate_operator``, ``predicate_value``,
        ``predicate_value2``) instead of a single ``dict``. The tool body
        rebuilds the ``QueryPredicate`` model from those inline args before
        calling the service layer."""
        from aerospike_cluster_manager_api.mcp.tools.query import query

        result_obj = SimpleNamespace(records=[], execution_time_ms=0, scanned_records=0, returned_records=0)
        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.query.query_service.execute_query",
                new=AsyncMock(return_value=result_obj),
            ) as exec_mock,
        ):
            await query(
                conn_id="conn-x",
                namespace="test",
                set_name="sample_set",
                predicate_bin="age",
                predicate_operator="between",
                predicate_value=18,
                predicate_value2=99,
            )

        assert exec_mock.await_args is not None
        body = exec_mock.await_args.args[1]
        assert body.predicate is not None
        assert body.predicate.bin == "age"
        assert body.predicate.operator == "between"
        assert body.predicate.value == 18
        assert body.predicate.value2 == 99

    async def test_truncated_flag_in_envelope(self) -> None:
        """When the service returns at-or-above the effective limit, the
        tool surfaces ``truncated=True`` in the envelope so the caller can
        re-issue with a tighter filter."""
        from aerospike_cluster_manager_api.mcp.tools.query import query

        # max_records=2 → effective_limit=2; returned_records=2 → truncated.
        recs = [
            _make_record(),
            _make_record(key=("test", "sample_set", "k2", b"\xde\xad")),
        ]
        result_obj = SimpleNamespace(records=recs, execution_time_ms=5, scanned_records=2, returned_records=2)
        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.query.query_service.execute_query",
                new=AsyncMock(return_value=result_obj),
            ),
        ):
            out = await query(
                conn_id="conn-x",
                namespace="test",
                set_name="sample_set",
                max_records=2,
            )

        assert out["truncated"] is True
        assert out["returned_records"] == 2

    async def test_truncated_false_when_below_limit(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools.query import query

        result_obj = SimpleNamespace(
            records=[_make_record()],
            execution_time_ms=1,
            scanned_records=1,
            returned_records=1,
        )
        mock_client = MagicMock()
        with (
            _patch_get_client(mock_client),
            patch(
                "aerospike_cluster_manager_api.mcp.tools.query.query_service.execute_query",
                new=AsyncMock(return_value=result_obj),
            ),
        ):
            out = await query(
                conn_id="conn-x",
                namespace="test",
                set_name="sample_set",
                max_records=10,
            )

        assert out["truncated"] is False

    async def test_missing_conn_id_raises_connection_not_found(self) -> None:
        from aerospike_cluster_manager_api.mcp.tools import query as query_tool

        with patch.object(
            query_tool.client_manager,
            "get_client",
            new=AsyncMock(side_effect=ValueError("no such conn")),
        ):
            try:
                await query_tool.query(conn_id="missing", namespace="test")
            except MCPToolError as exc:
                assert exc.code == "ConnectionNotFoundError"
            else:
                raise AssertionError("expected MCPToolError")

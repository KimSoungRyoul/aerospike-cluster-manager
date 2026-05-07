"""Tests for the CE-aware MCP error mapping layer.

The MCP tool wrappers (B.1+) and the registry decorator (A.12) translate
Aerospike-py exceptions and our own service-layer domain errors into
``MCPToolError`` instances with stable, user-facing wording. Unknown
exceptions must propagate untouched so the registry can log them and
surface a generic ``isError`` block without masking real bugs.

Wire-message wording follows
``docs/plans/2026-05-07-acm-mcp-design.md`` Section 4.
"""

from __future__ import annotations

import aerospike_py
import pytest

from aerospike_cluster_manager_api.mcp.errors import (
    MCPToolError,
    map_aerospike_errors,
    raise_ce_unsupported,
)
from aerospike_cluster_manager_api.services.clusters_service import (
    NamespaceConfigError,
    NamespaceNotFoundError,
    NodeNotFoundError,
)
from aerospike_cluster_manager_api.services.connections_service import (
    ConnectionNotFoundError,
    WorkspaceNotFoundError,
)
from aerospike_cluster_manager_api.services.records_service import (
    InvalidPkPattern,
    PrimaryKeyMissing,
    SetRequiredForPkLookup,
)

# ---------------------------------------------------------------------------
# MCPToolError shape
# ---------------------------------------------------------------------------


def test_mcp_tool_error_is_plain_exception_subclass() -> None:
    # Vanilla Exception keeps the registry's `except` clauses simple.
    assert issubclass(MCPToolError, Exception)
    assert not issubclass(MCPToolError, RuntimeError)


def test_mcp_tool_error_carries_message_and_optional_code() -> None:
    err = MCPToolError("boom", code="record_not_found")
    assert str(err) == "boom"
    assert err.code == "record_not_found"


def test_mcp_tool_error_code_defaults_to_none() -> None:
    err = MCPToolError("boom")
    assert err.code is None


# ---------------------------------------------------------------------------
# map_aerospike_errors — aerospike_py exceptions
# ---------------------------------------------------------------------------


def test_map_record_not_found_with_full_context() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors(ns="test", set_name="users", key="42"):
        raise aerospike_py.RecordNotFound("missing")

    err = exc_info.value
    assert str(err) == "Record not found: test/users/42"
    assert err.code == "record_not_found"
    # Original exception preserved as the cause for stack diagnosis.
    assert isinstance(err.__cause__, aerospike_py.RecordNotFound)


def test_map_record_not_found_without_context() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise aerospike_py.RecordNotFound("missing")

    assert str(exc_info.value) == "Record not found"
    assert exc_info.value.code == "record_not_found"


def test_map_record_exists_error_with_context() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors(ns="test", set_name="users", key=7):
        raise aerospike_py.RecordExistsError("exists")

    err = exc_info.value
    assert str(err) == "Record already exists: test/users/7"
    assert err.code == "record_exists"
    assert isinstance(err.__cause__, aerospike_py.RecordExistsError)


def test_map_record_exists_error_without_context() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise aerospike_py.RecordExistsError("exists")

    assert str(exc_info.value) == "Record already exists"
    assert exc_info.value.code == "record_exists"


def test_map_backpressure_error() -> None:
    """``aerospike_py.BackpressureError`` is mapped to a stable
    ``code="backpressure"`` so client-side wrappers (and operator
    dashboards) can apply retry-with-backoff without parsing the message.
    """
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise aerospike_py.BackpressureError("queue saturated")

    err = exc_info.value
    assert err.code == "backpressure"
    # Underlying client wording is preserved in the user-facing message.
    assert "queue saturated" in str(err)
    assert isinstance(err.__cause__, aerospike_py.BackpressureError)


def test_map_unknown_predicate_operator_to_invalid_argument() -> None:
    """``predicate.UnknownPredicateOperator`` is an input-validation
    failure — the predicate dispatch table did not recognise the operator.
    Mapped to ``code="invalid_argument"`` to match the SDK's standard
    family for malformed tool arguments.
    """
    from aerospike_cluster_manager_api.predicate import UnknownPredicateOperator

    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise UnknownPredicateOperator("frobnicate")

    err = exc_info.value
    assert err.code == "invalid_argument"
    assert "frobnicate" in str(err)
    assert isinstance(err.__cause__, UnknownPredicateOperator)


def test_map_info_verb_not_allowed_to_invalid_argument() -> None:
    """``info_verbs.InfoVerbNotAllowed`` shares the same wire family as
    ``UnknownPredicateOperator`` — the LLM should pick a different verb
    rather than escalate. ``code="invalid_argument"``, NOT
    ``access_denied`` (the tool itself is read-only-callable; the verb
    just isn't on the whitelist).
    """
    from aerospike_cluster_manager_api.info_verbs import InfoVerbNotAllowed

    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise InfoVerbNotAllowed("recluster")

    err = exc_info.value
    assert err.code == "invalid_argument"
    assert "recluster" in str(err)
    assert isinstance(err.__cause__, InfoVerbNotAllowed)


# ---------------------------------------------------------------------------
# map_aerospike_errors — service-layer domain exceptions
# ---------------------------------------------------------------------------


def test_map_connection_not_found_error() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise ConnectionNotFoundError("conn-abc123")

    err = exc_info.value
    assert "conn-abc123" in str(err)
    assert err.code == "ConnectionNotFoundError"
    assert isinstance(err.__cause__, ConnectionNotFoundError)


def test_map_workspace_not_found_error() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise WorkspaceNotFoundError("ws-1")

    err = exc_info.value
    assert "ws-1" in str(err)
    assert err.code == "WorkspaceNotFoundError"


def test_map_namespace_not_found_error() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise NamespaceNotFoundError("test")

    err = exc_info.value
    assert "test" in str(err)
    assert err.code == "NamespaceNotFoundError"


def test_map_node_not_found_error() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise NodeNotFoundError("BB9E0...")

    assert exc_info.value.code == "NodeNotFoundError"


def test_map_namespace_config_error() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise NamespaceConfigError("test", "ERROR::param-not-found")

    assert exc_info.value.code == "NamespaceConfigError"


def test_map_invalid_pk_pattern() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise InvalidPkPattern("bad regex")

    assert str(exc_info.value) == "bad regex"
    assert exc_info.value.code == "InvalidPkPattern"


def test_map_set_required_for_pk_lookup() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise SetRequiredForPkLookup()

    assert exc_info.value.code == "SetRequiredForPkLookup"


def test_map_primary_key_missing() -> None:
    with pytest.raises(MCPToolError) as exc_info, map_aerospike_errors():
        raise PrimaryKeyMissing("namespace")

    assert exc_info.value.code == "PrimaryKeyMissing"


# ---------------------------------------------------------------------------
# Pass-through: unknown errors propagate unchanged so the registry can log
# them and avoid swallowing real bugs.
# ---------------------------------------------------------------------------


def test_generic_exception_propagates_unchanged() -> None:
    with pytest.raises(RuntimeError, match="boom"), map_aerospike_errors():
        raise RuntimeError("boom")


def test_unmapped_aerospike_error_propagates_unchanged() -> None:
    # ``AerospikeError`` is the base class — only specific known subclasses
    # are mapped. Anything else bubbles up.
    with pytest.raises(aerospike_py.exception.AerospikeError), map_aerospike_errors():
        raise aerospike_py.exception.ClientError("client failure")


def test_no_exception_passes_through_cleanly() -> None:
    with map_aerospike_errors(ns="test"):
        result = 1 + 1
    assert result == 2


# ---------------------------------------------------------------------------
# raise_ce_unsupported helper — Phase 2 K8s tools and CE-rejected ops
# ---------------------------------------------------------------------------


def test_raise_ce_unsupported_message_and_code() -> None:
    with pytest.raises(MCPToolError) as exc_info:
        raise_ce_unsupported("XDR shipping")

    err = exc_info.value
    assert str(err) == "This operation is not supported on Aerospike CE 8.1: XDR shipping"
    assert err.code == "ce_unsupported"

"""Tests for the MCP access profile gate.

The access profile is a call-time read-only mode: it lets the MCP
registry expose all tools to the model, but blocks writes at call time
when the deployment is configured ``READ_ONLY``. ``execute_info`` and
``execute_info_on_node`` are intentionally classified as WRITE because
asinfo can mutate cluster configuration (e.g. ``set-config``).

These tests cover:
* the public surface of ``access_profile.py`` (``AccessProfile``,
  ``is_blocked``, ``parse_profile``);
* the ``ACM_MCP_ACCESS_PROFILE`` env var wiring in ``config.py`` —
  default ``READ_ONLY`` when unset, parsed strictly otherwise.
"""

from __future__ import annotations

import importlib

import pytest

from aerospike_cluster_manager_api.mcp.access_profile import (
    AccessProfile,
    is_blocked,
    parse_profile,
)

# ---------------------------------------------------------------------------
# is_blocked — read-only profile blocks writes, allows reads
# ---------------------------------------------------------------------------


def test_is_blocked_read_tool_under_read_only_is_false() -> None:
    assert is_blocked("get_record", AccessProfile.READ_ONLY) is False


def test_is_blocked_create_record_under_read_only_is_true() -> None:
    assert is_blocked("create_record", AccessProfile.READ_ONLY) is True


def test_is_blocked_create_record_under_full_is_false() -> None:
    assert is_blocked("create_record", AccessProfile.FULL) is False


def test_is_blocked_delete_record_under_read_only_is_true() -> None:
    assert is_blocked("delete_record", AccessProfile.READ_ONLY) is True


def test_is_blocked_execute_info_under_read_only_is_true() -> None:
    # asinfo can mutate config (set-config, etc.) — must be classified WRITE.
    assert is_blocked("execute_info", AccessProfile.READ_ONLY) is True


def test_is_blocked_list_namespaces_under_read_only_is_false() -> None:
    assert is_blocked("list_namespaces", AccessProfile.READ_ONLY) is False


def test_is_blocked_unknown_tool_under_read_only_is_false() -> None:
    """Unknown tools are not blocked: registry decides existence; profile filters."""
    assert is_blocked("does_not_exist", AccessProfile.READ_ONLY) is False


def test_is_blocked_unknown_tool_under_full_is_false() -> None:
    assert is_blocked("does_not_exist", AccessProfile.FULL) is False


# ---------------------------------------------------------------------------
# parse_profile — case-insensitive; ValueError on unknown
# ---------------------------------------------------------------------------


def test_parse_profile_read_only_lower() -> None:
    assert parse_profile("read_only") is AccessProfile.READ_ONLY


def test_parse_profile_full_uppercase() -> None:
    assert parse_profile("FULL") is AccessProfile.FULL


def test_parse_profile_with_surrounding_whitespace() -> None:
    assert parse_profile("  read_only  ") is AccessProfile.READ_ONLY


def test_parse_profile_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="garbage"):
        parse_profile("garbage")


def test_parse_profile_unknown_lists_valid_values_in_message() -> None:
    with pytest.raises(ValueError) as exc:
        parse_profile("garbage")
    msg = str(exc.value)
    assert "full" in msg
    assert "read_only" in msg


# ---------------------------------------------------------------------------
# config.ACM_MCP_ACCESS_PROFILE — default READ_ONLY; parsed via parse_profile
# ---------------------------------------------------------------------------


def test_config_default_access_profile_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ACM_MCP_ACCESS_PROFILE", raising=False)
    from aerospike_cluster_manager_api import config as _config

    importlib.reload(_config)
    try:
        assert _config.ACM_MCP_ACCESS_PROFILE is AccessProfile.READ_ONLY
    finally:
        importlib.reload(_config)


def test_config_access_profile_full_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACM_MCP_ACCESS_PROFILE", "full")
    from aerospike_cluster_manager_api import config as _config

    importlib.reload(_config)
    try:
        assert _config.ACM_MCP_ACCESS_PROFILE is AccessProfile.FULL
    finally:
        monkeypatch.delenv("ACM_MCP_ACCESS_PROFILE", raising=False)
        importlib.reload(_config)


def test_config_access_profile_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACM_MCP_ACCESS_PROFILE", "garbage")
    from aerospike_cluster_manager_api import config as _config

    try:
        with pytest.raises(ValueError, match="garbage"):
            importlib.reload(_config)
    finally:
        monkeypatch.delenv("ACM_MCP_ACCESS_PROFILE", raising=False)
        importlib.reload(_config)

"""MCP tool registration decorator (registry).

Phase 1 tools (B.1+) decorate themselves with :func:`tool` at import time.
Each decoration:

* records :class:`ToolMetadata` (name, category, mutation, callable) in
  the module-level ``_REGISTRY`` accumulator;
* wraps the function with the access-profile gate (A.8) — mutation tools
  named in ``access_profile.WRITE_TOOLS`` raise
  :class:`MCPToolError` with ``code="access_denied"`` under the
  ``READ_ONLY`` profile, **before** the body runs;
* wraps the function with :func:`map_aerospike_errors` (A.11) so known
  service-layer errors surface as :class:`MCPToolError` with stable codes
  while everything else propagates so the registry / OTel pipeline can
  log the real bug.

The decorator returns the *wrapped* form so tests and other callers that
bypass FastMCP still see the gate. ``register_all(mcp)`` is invoked once
from :func:`build_mcp_app` (B.6) to flush the accumulator into a single
:class:`FastMCP` instance via :meth:`FastMCP.add_tool`.

Read the module docstring of :mod:`access_profile` for why blocking is
done at the call site rather than at registration time.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP

from aerospike_cluster_manager_api import config
from aerospike_cluster_manager_api.mcp.access_profile import AccessProfile, is_blocked
from aerospike_cluster_manager_api.mcp.errors import MCPToolError, map_aerospike_errors


@dataclass(frozen=True)
class ToolMetadata:
    """Snapshot of a registered tool — exposed for autodiscovery / docs.

    ``func`` is the *wrapped* callable (with access-profile + error-mapping
    already applied). Direct callers see the same gate as FastMCP would.
    """

    name: str
    category: str
    mutation: bool
    func: Callable[..., Any]


_REGISTRY: list[ToolMetadata] = []


def tool(
    *,
    category: str,
    mutation: bool = False,
    name: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function as an MCP tool.

    Parameters
    ----------
    category:
        Free-form grouping label (e.g. ``"record"``, ``"connection"``,
        ``"cluster"``) used by introspection and docs generation.
    mutation:
        ``True`` for tools that mutate state. Combined with the
        :data:`access_profile.WRITE_TOOLS` list to decide whether the
        ``READ_ONLY`` profile must reject the call. Tools whose names are
        not in ``WRITE_TOOLS`` run under ``READ_ONLY`` regardless of this
        flag (default-allow); the flag is purely for introspection.
    name:
        Optional override; defaults to ``func.__name__``. Must be unique
        across the registry — duplicates raise :class:`ValueError`.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__
        if any(entry.name == tool_name for entry in _REGISTRY):
            raise ValueError(f"Duplicate tool registration: {tool_name}")

        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            profile: AccessProfile = config.ACM_MCP_ACCESS_PROFILE
            if mutation and is_blocked(tool_name, profile):
                raise MCPToolError(
                    f"Tool '{tool_name}' is disabled by access profile '{profile.value}'.",
                    code="access_denied",
                )
            with map_aerospike_errors():
                if is_async:
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

        _REGISTRY.append(ToolMetadata(name=tool_name, category=category, mutation=mutation, func=wrapped))
        return wrapped

    return decorator


def register_all(mcp: FastMCP) -> int:
    """Wire every accumulated tool into ``mcp`` and return the count.

    Called once by :func:`build_mcp_app` (B.6). Invoking it on an empty
    registry returns ``0`` and leaves ``mcp`` untouched.
    """
    for entry in _REGISTRY:
        mcp.add_tool(entry.func, name=entry.name)
    return len(_REGISTRY)


def registered_tools() -> list[ToolMetadata]:
    """Return a snapshot copy of the current registry.

    Useful for introspection (docs, ``__repr__``, telemetry); callers
    should not mutate the result — modifying the returned list does not
    affect the registry.
    """
    return list(_REGISTRY)


def _reset_for_tests() -> None:
    """Test helper: clear the module-level registry. **Not for production.**

    Phase 1 tool modules decorate at import time, so tests reset between
    cases to avoid cross-test bleed. Production code calls
    :func:`register_all` exactly once from :func:`build_mcp_app`.
    """
    _REGISTRY.clear()

"""MCP tools for Aerospike record CRUD (Voyager parity).

This module exposes 7 record tools that wrap the existing service layer
(:mod:`aerospike_cluster_manager_api.services.records_service`) and the
live-client pool (:mod:`aerospike_cluster_manager_api.client_manager`):

* ``get_record`` — read by primary key
* ``record_exists`` — existence probe (no bins fetched)
* ``create_record`` — create-only write (mutation)
* ``update_record`` — update-only write (mutation)
* ``delete_record`` — remove a record (mutation)
* ``delete_bin`` — remove a single bin from a record (mutation)
* ``truncate_set`` — drop every record in a set, optionally up to a LUT (mutation)

Design notes:

* Tools accept simple Python types (``str``, ``int``, ``dict``) so the
  MCP SDK can derive a JSON Schema directly from the type hints.
* Reads return ``serialize_record`` envelopes (see :mod:`mcp.serializers`)
  so CDT bytes round-trip safely as the documented base64 marker dict.
* Mutations return small ack dicts so the model can confirm side-effects:
  ``{"created": True, ...}``, ``{"updated": True, ...}``, etc.
* Keys are ``str | int`` at the MCP boundary — Voyager parity. The service
  layer's auto pk-type heuristic resolves numeric strings into integers
  automatically, so the model can speak in either form. We always pass
  ``"auto"`` from this module; advanced pk-type semantics stay below the
  REST surface.
* The ``@tool`` decorator already wraps every body in the access-profile
  gate and ``map_aerospike_errors`` — do **not** apply them again here.
* ``client_manager.get_client`` raises :class:`ValueError` when the profile
  is missing; we re-raise as :class:`ConnectionNotFoundError` so the
  registry's error map produces the canonical
  ``code="ConnectionNotFoundError"`` wire shape, matching the read-side
  tools (B.1, B.2).
"""

from __future__ import annotations

from typing import Any

from aerospike_cluster_manager_api.client_manager import client_manager
from aerospike_cluster_manager_api.mcp.registry import tool
from aerospike_cluster_manager_api.mcp.serializers import serialize_record
from aerospike_cluster_manager_api.services import records_service
from aerospike_cluster_manager_api.services.connections_service import (
    ConnectionNotFoundError,
)


async def _get_client(conn_id: str) -> Any:
    """Resolve a live ``AsyncClient`` for ``conn_id``.

    See module docstring — translates ``ValueError`` (the shape
    ``client_manager`` raises for unknown profiles) into the canonical
    :class:`ConnectionNotFoundError` so the registry error map produces a
    stable wire code.
    """
    try:
        return await client_manager.get_client(conn_id)
    except ValueError as e:
        raise ConnectionNotFoundError(conn_id) from e


def _key_envelope(namespace: str, set_name: str, key: str | int) -> dict[str, Any]:
    """Build the ``{"namespace", "set", "pk"}`` ack envelope used by writes."""
    return {"namespace": namespace, "set": set_name, "pk": key}


@tool(category="record", mutation=False)
async def get_record(
    conn_id: str,
    namespace: str,
    set_name: str,
    key: str | int,
) -> dict[str, Any]:
    """Fetch a single record by ``(namespace, set, key)``.

    Returns the standard MCP record envelope: ``{"key", "meta", "bins"}``
    (see :mod:`mcp.serializers`). ``MCPToolError`` with
    ``code="record_not_found"`` is raised when no record exists at the key.
    """
    client = await _get_client(conn_id)
    record = await records_service.get_record(client, namespace, set_name, str(key))
    return serialize_record(record)


@tool(category="record", mutation=False)
async def record_exists(
    conn_id: str,
    namespace: str,
    set_name: str,
    key: str | int,
) -> dict[str, Any]:
    """Probe whether a record exists at ``(namespace, set, key)``.

    Returns ``{"exists": bool}`` — never raises ``record_not_found``.
    Useful for cheap pre-flight checks before larger reads.
    """
    client = await _get_client(conn_id)
    exists = await records_service.record_exists(client, namespace, set_name, str(key))
    return {"exists": exists}


@tool(category="record", mutation=True)
async def create_record(
    conn_id: str,
    namespace: str,
    set_name: str,
    key: str | int,
    bins: dict[str, Any],
) -> dict[str, Any]:
    """Create a record, failing if one already exists at the same key.

    Uses the ``CREATE_ONLY`` write policy; collisions surface as
    :class:`MCPToolError` with ``code="record_exists"``.

    Returns ``{"created": True, "key": {...}}``.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    await records_service.create_record(client, namespace, set_name, str(key), bins)
    return {"created": True, "key": _key_envelope(namespace, set_name, key)}


@tool(category="record", mutation=True)
async def update_record(
    conn_id: str,
    namespace: str,
    set_name: str,
    key: str | int,
    bins: dict[str, Any],
) -> dict[str, Any]:
    """Update an existing record, failing if it is absent.

    Uses the ``UPDATE_ONLY`` write policy; missing records surface as
    :class:`MCPToolError` with ``code="record_not_found"``.

    Returns ``{"updated": True, "key": {...}}``.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    await records_service.update_record(client, namespace, set_name, str(key), bins)
    return {"updated": True, "key": _key_envelope(namespace, set_name, key)}


@tool(category="record", mutation=True)
async def delete_record(
    conn_id: str,
    namespace: str,
    set_name: str,
    key: str | int,
) -> dict[str, Any]:
    """Delete a record by ``(namespace, set, key)``.

    Returns ``{"deleted": True, "key": {...}}``. Missing records surface as
    :class:`MCPToolError` with ``code="record_not_found"``.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    await records_service.delete_record(client, namespace, set_name, str(key))
    return {"deleted": True, "key": _key_envelope(namespace, set_name, key)}


@tool(category="record", mutation=True)
async def delete_bin(
    conn_id: str,
    namespace: str,
    set_name: str,
    key: str | int,
    bin_name: str,
) -> dict[str, Any]:
    """Remove a single bin from a record (sets the bin to nil server-side).

    Note that removing the last bin from a record makes the whole record
    disappear server-side — this is standard Aerospike behaviour and not
    something the tool papers over.

    Returns ``{"bin_deleted": True, "bin": "...", "key": {...}}``.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    await records_service.delete_bin(client, namespace, set_name, str(key), bin_name)
    return {
        "bin_deleted": True,
        "bin": bin_name,
        "key": _key_envelope(namespace, set_name, key),
    }


@tool(category="record", mutation=True)
async def truncate_set(
    conn_id: str,
    namespace: str,
    set_name: str,
    before_lut: int | None = None,
) -> dict[str, Any]:
    """Truncate every record in ``namespace.set_name`` (or up to ``before_lut``).

    ``before_lut`` is the cutoff in nanoseconds since CITRUS epoch — when
    omitted, every record currently in the set is cleared.

    Returns ``{"truncated": True, "namespace": "...", "set": "..."}``.

    Mutation: requires ``ACM_MCP_ACCESS_PROFILE=full``; returns
    ``code=access_denied`` under READ_ONLY.
    """
    client = await _get_client(conn_id)
    await records_service.truncate_set(client, namespace, set_name, before_lut=before_lut)
    return {"truncated": True, "namespace": namespace, "set": set_name}

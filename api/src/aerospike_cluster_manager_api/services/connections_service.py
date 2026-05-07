"""Business logic for Aerospike connection profile management.

These functions are the single source of truth for the connection lifecycle
(list / get / create / update / delete / test). They are called by both:

* the HTTP router (``routers/connections.py``) — which wraps them in
  HTTPException translation, rate-limiting, and FastAPI dependencies, and
* the MCP tool layer (added in a later task) — which calls them directly
  from MCP tool handlers.

To stay reusable from both sides, this module **must not** import ``fastapi``
or other HTTP-shaping libraries. Domain failures are signalled by plain
exceptions defined here, which the router translates to HTTP status codes.
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import aerospike_py
from aerospike_py.exception import AerospikeError

from aerospike_cluster_manager_api import db
from aerospike_cluster_manager_api.client_manager import client_manager
from aerospike_cluster_manager_api.models.connection import (
    ConnectionProfile,
    ConnectionProfileResponse,
    CreateConnectionRequest,
    TestConnectionRequest,
    UpdateConnectionRequest,
)
from aerospike_cluster_manager_api.models.workspace import DEFAULT_WORKSPACE_ID
from aerospike_cluster_manager_api.utils import parse_host_port

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class ConnectionNotFoundError(LookupError):
    """Raised when a connection profile is not found by id."""

    def __init__(self, conn_id: str) -> None:
        super().__init__(f"Connection '{conn_id}' not found")
        self.conn_id = conn_id


class WorkspaceNotFoundError(LookupError):
    """Raised when a referenced workspace does not exist."""

    def __init__(self, workspace_id: str) -> None:
        super().__init__(f"Workspace '{workspace_id}' not found")
        self.workspace_id = workspace_id


# ---------------------------------------------------------------------------
# Service entry points
# ---------------------------------------------------------------------------


async def list_connections(workspace_id: str | None) -> list[ConnectionProfileResponse]:
    """Return all saved connection profiles, optionally filtered by workspace.

    Raises ``WorkspaceNotFoundError`` if a non-None ``workspace_id`` is
    provided and no such workspace exists.
    """
    if workspace_id is not None:
        ws = await db.get_workspace(workspace_id)
        if not ws:
            raise WorkspaceNotFoundError(workspace_id)
    profiles = await db.get_all_connections(workspace_id)
    return [ConnectionProfileResponse.from_profile(p) for p in profiles]


async def get_connection(conn_id: str) -> ConnectionProfileResponse:
    """Return the connection profile with id ``conn_id``.

    Raises ``ConnectionNotFoundError`` if no such profile exists.
    """
    conn = await db.get_connection(conn_id)
    if not conn:
        raise ConnectionNotFoundError(conn_id)
    return ConnectionProfileResponse.from_profile(conn)


async def create_connection(payload: CreateConnectionRequest) -> ConnectionProfileResponse:
    """Persist a new connection profile and return it (without password).

    Falls back to ``DEFAULT_WORKSPACE_ID`` when the request omits the workspace.
    Raises ``WorkspaceNotFoundError`` if the resolved workspace does not exist.
    """
    workspace_id = payload.workspaceId or DEFAULT_WORKSPACE_ID
    if not await db.get_workspace(workspace_id):
        raise WorkspaceNotFoundError(workspace_id)

    now = datetime.now(UTC).isoformat()
    conn = ConnectionProfile(
        id=f"conn-{uuid.uuid4().hex[:12]}",
        name=payload.name,
        hosts=payload.hosts,
        port=payload.port,
        clusterName=payload.clusterName,
        username=payload.username,
        password=payload.password,
        color=payload.color,
        description=payload.description,
        labels=payload.labels or {},
        workspaceId=workspace_id,
        createdAt=now,
        updatedAt=now,
    )
    await db.create_connection(conn)
    return ConnectionProfileResponse.from_profile(conn)


async def update_connection(conn_id: str, payload: UpdateConnectionRequest) -> ConnectionProfileResponse:
    """Apply a partial update to ``conn_id`` and return the new state.

    Raises ``ConnectionNotFoundError`` if the connection does not exist, or
    ``WorkspaceNotFoundError`` if the request moves it to a missing workspace.
    """
    update_data = payload.model_dump(exclude_unset=True, by_alias=False)
    if "workspaceId" in update_data and update_data["workspaceId"] is not None:
        target_ws = update_data["workspaceId"]
        if not await db.get_workspace(target_ws):
            raise WorkspaceNotFoundError(target_ws)

    conn = await db.update_connection(conn_id, update_data)
    if not conn:
        raise ConnectionNotFoundError(conn_id)
    return ConnectionProfileResponse.from_profile(conn)


async def delete_connection(conn_id: str) -> None:
    """Delete a connection profile and close its cached Aerospike client.

    Idempotent: deleting a missing connection is a no-op (mirrors the
    router's pre-refactor behaviour, which always returned 204).
    """
    await db.delete_connection(conn_id)
    await client_manager.close_client(conn_id)


async def test_connection(req: TestConnectionRequest) -> dict[str, Any]:
    """Probe Aerospike connectivity without persisting a profile.

    Returns ``{"success": bool, "message": str}``. Never raises — any error
    is captured and surfaced as ``success=False``.
    """
    try:
        hosts = [parse_host_port(h, req.port) for h in req.hosts]

        config: dict[str, Any] = {"hosts": hosts}
        if req.username and req.password:
            config["user"] = req.username
            config["password"] = req.password

        client = aerospike_py.AsyncClient(config)
        await client.connect()
        try:
            if not client.is_connected():
                return {"success": False, "message": "Failed to connect"}
            return {"success": True, "message": "Connected successfully"}
        finally:
            with contextlib.suppress(AerospikeError, OSError):
                await client.close()
    except Exception as e:
        logger.exception("Test connection failed")
        return {"success": False, "message": str(e)}

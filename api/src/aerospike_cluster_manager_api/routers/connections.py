from __future__ import annotations

import asyncio
import logging
from typing import Any

import aerospike_py  # noqa: F401  — re-exported for tests that patch via this module path
from aerospike_py.exception import AerospikeError, AerospikeTimeoutError, ClusterError
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import Response

from aerospike_cluster_manager_api.client_manager import client_manager
from aerospike_cluster_manager_api.constants import INFO_BUILD, INFO_EDITION, INFO_NAMESPACES
from aerospike_cluster_manager_api.dependencies import _get_verified_connection
from aerospike_cluster_manager_api.info_parser import parse_kv_pairs, parse_list, safe_int
from aerospike_cluster_manager_api.models.connection import (
    ConnectionProfileResponse,
    ConnectionStatus,
    CreateConnectionRequest,
    TestConnectionRequest,
    UpdateConnectionRequest,
)
from aerospike_cluster_manager_api.rate_limit import limiter
from aerospike_cluster_manager_api.services import connections_service
from aerospike_cluster_manager_api.services.connections_service import (
    ConnectionNotFoundError,
    WorkspaceNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", summary="List connections", description="Retrieve all saved Aerospike connection profiles.")
async def list_connections(
    workspace_id: str | None = Query(default=None, description="Filter by workspace id."),
) -> list[ConnectionProfileResponse]:
    """Retrieve all saved Aerospike connection profiles, optionally filtered by workspace."""
    try:
        return await connections_service.list_connections(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", status_code=201, summary="Create connection", description="Create a new Aerospike connection profile.")
@limiter.limit("10/minute")
async def create_connection(request: Request, body: CreateConnectionRequest) -> ConnectionProfileResponse:
    """Create a new Aerospike connection profile."""
    try:
        return await connections_service.create_connection(body)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{conn_id}", summary="Get connection", description="Retrieve a single connection profile by its ID.")
async def get_connection(conn_id: str = Depends(_get_verified_connection)) -> ConnectionProfileResponse:
    """Retrieve a single connection profile by its ID."""
    try:
        return await connections_service.get_connection(conn_id)
    except ConnectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/{conn_id}", summary="Update connection", description="Update an existing connection profile with new settings."
)
async def update_connection(
    body: UpdateConnectionRequest,
    conn_id: str = Depends(_get_verified_connection),
) -> ConnectionProfileResponse:
    """Update an existing connection profile with new settings."""
    try:
        return await connections_service.update_connection(conn_id, body)
    except ConnectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{conn_id}/health",
    summary="Check connection health",
    description="Check the health status of an Aerospike cluster connection.",
    response_model=None,
)
async def get_connection_health(conn_id: str = Depends(_get_verified_connection)) -> ConnectionStatus | Response:
    """Check the health status of an Aerospike cluster connection.

    Always returns HTTP 200. Uses ``connected: false`` to signal unreachable clusters
    so that the frontend health indicator never mistakes a transient 503 for a permanent failure.
    """
    try:
        client = await client_manager.get_client(conn_id)

        # get_node_names() is synchronous — call it before the async gather
        node_names = client.get_node_names()

        # Fetch namespace list, build, and edition in parallel
        ns_raw, build_raw, edition_raw = await asyncio.gather(
            client.info_random_node(INFO_NAMESPACES),
            client.info_random_node(INFO_BUILD),
            client.info_random_node(INFO_EDITION),
        )
        namespaces = parse_list(ns_raw)
        build = build_raw.strip()
        edition = edition_raw.strip()
        node_count = len(node_names)

        # Collect namespace-level summary metrics
        memory_used = 0
        memory_total = 0
        disk_used = 0
        disk_total = 0

        try:
            # Fetch all namespace info in parallel
            if namespaces:
                ns_infos = await asyncio.gather(
                    *[client.info_random_node(f"namespace/{ns_name}") for ns_name in namespaces]
                )
            else:
                ns_infos = []

            for ns_info in ns_infos:
                kv = parse_kv_pairs(ns_info)
                # CE 8 uses unified data_used_bytes/data_total_bytes for both memory and device.
                # Fall back to legacy memory_used_bytes/memory-size for older versions.
                ns_data_used = (
                    safe_int(kv.get("data_used_bytes"))
                    if "data_used_bytes" in kv
                    else safe_int(kv.get("memory_used_bytes"))
                )
                ns_data_total = (
                    safe_int(kv.get("data_total_bytes"))
                    if "data_total_bytes" in kv
                    else safe_int(kv.get("memory-size"))
                )
                # Multiply per-node values by node count for cluster-wide estimate
                memory_used += ns_data_used * node_count
                memory_total += ns_data_total * node_count
                disk_used += safe_int(kv.get("device_used_bytes")) * node_count
                disk_total += safe_int(kv.get("device-total-bytes")) * node_count
        except Exception:
            logger.debug("Failed to collect namespace stats for connection '%s'", conn_id, exc_info=True)

        return ConnectionStatus(
            connected=True,
            nodeCount=node_count,
            namespaceCount=len(namespaces),
            build=build,
            edition=edition,
            memoryUsed=memory_used,
            memoryTotal=memory_total,
            diskUsed=disk_used,
            diskTotal=disk_total,
            tendHealthy=await client.ping(),  # type: ignore[attr-defined]  # ping() added in aerospike-py 0.0.5
        )
    except AerospikeTimeoutError as exc:
        logger.warning("Health check timed out for connection '%s'", conn_id, exc_info=True)
        return _disconnected_health(str(exc), "timeout")
    except ConnectionRefusedError as exc:
        logger.warning("Connection refused for '%s'", conn_id, exc_info=True)
        return _disconnected_health(str(exc), "connection_refused")
    except ClusterError as exc:
        logger.warning("Cluster error for connection '%s'", conn_id, exc_info=True)
        return _disconnected_health(str(exc), "cluster_error")
    except (AerospikeError, OSError) as exc:
        logger.warning("Health check failed for connection '%s'", conn_id, exc_info=True)
        error_type = "auth_error" if isinstance(exc, AerospikeError) and "security" in str(exc).lower() else "unknown"
        return _disconnected_health(str(exc), error_type)


def _disconnected_health(error: str, error_type: str) -> Response:
    """Build a JSON Response for the ``connected=false`` health-check shape."""
    return Response(
        content=ConnectionStatus(
            connected=False, nodeCount=0, namespaceCount=0, error=error, errorType=error_type
        ).model_dump_json(),
        media_type="application/json",
        headers={"Retry-After": "30"},
    )


@router.post(
    "/test",
    summary="Test connection",
    description="Test connectivity to an Aerospike cluster without saving the profile.",
)
@limiter.limit("5/minute")
async def test_connection(request: Request, body: TestConnectionRequest) -> dict[str, Any]:
    """Test connectivity to an Aerospike cluster without saving the profile."""
    return await connections_service.test_connection(body)


@router.delete(
    "/{conn_id}",
    status_code=204,
    summary="Delete connection",
    description="Delete a connection profile and close its active client.",
)
@limiter.limit("10/minute")
async def delete_connection(request: Request, conn_id: str = Depends(_get_verified_connection)) -> Response:
    """Delete a connection profile and close its active client."""
    await connections_service.delete_connection(conn_id)
    return Response(status_code=204)

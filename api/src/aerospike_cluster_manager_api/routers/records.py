from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import Response

from aerospike_cluster_manager_api.converters import record_to_model
from aerospike_cluster_manager_api.dependencies import AerospikeClient
from aerospike_cluster_manager_api.models.query import FilteredQueryRequest, FilteredQueryResponse
from aerospike_cluster_manager_api.models.record import (
    AerospikeRecord,
    RecordListResponse,
    RecordWriteRequest,
)
from aerospike_cluster_manager_api.services import records_service
from aerospike_cluster_manager_api.services.records_service import (
    InvalidPkPattern,
    PrimaryKeyMissing,
    SetRequiredForPkLookup,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/records", tags=["records"])


@router.get(
    "/{conn_id}",
    summary="List records",
    description="Retrieve records from a namespace and set with a server-side limit.",
)
async def get_records(
    client: AerospikeClient,
    ns: str = Query(..., min_length=1),
    set: str = "",
    pageSize: int = Query(25, ge=1, le=500),
) -> RecordListResponse:
    """Retrieve records from a namespace and set (limited by pageSize).

    Note: if any record in the scan stream contains a particle type the native
    client cannot decode (e.g. PYTHON_BLOB / JAVA_BLOB written by a legacy
    language-specific client — see aerospike-py issue #280), the underlying
    aerospike-core stream is broken at that record and the whole request
    surfaces as HTTP 422 (``RustPanicError``). Per-record skipping is not
    available without an aerospike-core fork.
    """
    result = await records_service.list_records(client, ns, set, page_size=pageSize)
    return RecordListResponse(
        records=[record_to_model(r) for r in result.records],
        total=result.total,
        page=result.page,
        pageSize=result.page_size,
        hasMore=result.has_more,
        totalEstimated=result.total_estimated,
    )


@router.get(
    "/{conn_id}/detail",
    summary="Get record detail",
    description="Retrieve a single record identified by namespace, set, and primary key.",
)
async def get_record_detail(
    client: AerospikeClient,
    ns: str = Query(..., min_length=1),
    set: str = Query(...),
    pk: str = Query(..., min_length=1),
    pk_type: Literal["auto", "string", "int", "bytes"] = Query("auto"),
) -> AerospikeRecord:
    """Retrieve a single record identified by namespace, set, and primary key.

    When ``pk_type='auto'`` (default), the lookup falls back to the alternate
    particle type on NOT_FOUND — fixing the case where a numeric-string key
    (e.g. ``"23404907"``) was stored as STRING but would otherwise be probed
    as INTEGER. Pass an explicit ``pk_type`` to disable the fallback.
    """
    try:
        raw_result = await records_service.get_record(client, ns, set, pk, pk_type)
    except ValueError as exc:
        # Explicit pk_type with unparseable pk → 400.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record_to_model(raw_result)


@router.post(
    "/{conn_id}",
    status_code=201,
    summary="Create or update record",
    description="Write a record to Aerospike with the specified key, bins, and optional TTL.",
)
async def put_record(body: RecordWriteRequest, client: AerospikeClient) -> AerospikeRecord:
    """Write a record to Aerospike with the specified key, bins, and optional TTL.

    The key's particle type comes from ``body.key.pk_type`` ("auto" by default).
    Writes do not fall back: the resolved type is what gets persisted on disk,
    so callers that care should pass an explicit ``pk_type`` to avoid creating
    a record under a particle type that subsequent reads can't find.
    """
    try:
        result = await records_service.put_record(client, body)
    except PrimaryKeyMissing as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record_to_model(result)


@router.delete(
    "/{conn_id}",
    status_code=204,
    summary="Delete record",
    description="Delete a record identified by namespace, set, and primary key.",
)
async def delete_record(
    client: AerospikeClient,
    ns: str = Query(..., min_length=1),
    set: str = Query(..., min_length=1),
    pk: str = Query(..., min_length=1),
    pk_type: Literal["auto", "string", "int", "bytes"] = Query("auto"),
) -> Response:
    """Delete a record identified by namespace, set, and primary key.

    Deletes do not fall back to the alternate type even in ``auto`` mode: a
    delete that targets the wrong particle type would silently no-op (the
    record at the *other* type stays put), and a fallback could mask that
    fact. Pass an explicit ``pk_type`` to be sure of which record gets removed.
    """
    try:
        await records_service.delete_record(client, ns, set, pk, pk_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post(
    "/{conn_id}/filter",
    summary="Filtered record scan",
    description="Scan records with optional expression filters and pagination.",
)
async def get_filtered_records(
    body: FilteredQueryRequest,
    client: AerospikeClient,
) -> FilteredQueryResponse:
    """Scan records with optional expression filters and pagination."""
    try:
        result = await records_service.filter_records(client, body)
    except SetRequiredForPkLookup as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidPkPattern as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FilteredQueryResponse(
        records=[record_to_model(r) for r in result.records],
        total=result.total,
        page=result.page,
        pageSize=result.page_size,
        hasMore=result.has_more,
        executionTimeMs=result.execution_time_ms,
        scannedRecords=result.scanned_records,
        returnedRecords=result.returned_records,
        totalEstimated=result.total_estimated,
    )

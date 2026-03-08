from __future__ import annotations

import logging
import secrets
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter

from aerospike_cluster_manager_api.constants import POLICY_WRITE
from aerospike_cluster_manager_api.dependencies import AerospikeClient
from aerospike_cluster_manager_api.lua_modules import get_lua_modules
from aerospike_cluster_manager_api.models.sample_data import CreateSampleDataRequest, CreateSampleDataResponse
from aerospike_cluster_manager_api.sample_data_generator import SAMPLE_INDEXES, generate_record_bins

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sample-data", tags=["sample-data"])


@router.post(
    "/{conn_id}",
    status_code=201,
    summary="Create sample data set",
    description="Generate deterministic sample records with optional secondary indexes and UDF registration.",
)
async def create_sample_data(
    body: CreateSampleDataRequest,
    client: AerospikeClient,
) -> CreateSampleDataResponse:
    start = time.monotonic()
    ns = body.namespace
    set_name = body.set_name
    count = body.record_count

    # 1. Insert records
    records_created = 0
    for i in range(1, count + 1):
        key_tuple = (ns, set_name, i)
        bins = generate_record_bins(i)
        await client.put(key_tuple, bins, policy=POLICY_WRITE)
        records_created += 1

    # Short random suffix to avoid name collisions across multiple invocations.
    suffix = secrets.token_hex(3)  # e.g. "a3f2b1"

    # 2. Create secondary indexes (if requested)
    indexes_created: list[str] = []
    indexes_skipped: list[str] = []
    if body.create_indexes:
        for idx_name, bin_name, idx_type in SAMPLE_INDEXES:
            actual_idx_name = f"{idx_name}_{suffix}"
            try:
                if idx_type == "numeric":
                    await client.index_integer_create(ns, set_name, bin_name, actual_idx_name)
                elif idx_type == "string":
                    await client.index_string_create(ns, set_name, bin_name, actual_idx_name)
                elif idx_type == "geo2dsphere":
                    await client.index_geo2dsphere_create(ns, set_name, bin_name, actual_idx_name)
                indexes_created.append(actual_idx_name)
            except Exception as exc:
                # aerospike_py 0.0.1 has a bug where IndexFoundError is not properly mapped
                # and surfaces as a generic ClientError with "IndexFound" in the message.
                # Catch both the mapped and unmapped variants.
                if "IndexFound" in str(exc) or "already exists" in str(exc):
                    indexes_skipped.append(actual_idx_name)
                    logger.info("Index %s already exists, skipping", actual_idx_name)
                else:
                    raise

    # 3. Register UDFs (if requested)
    udfs_registered: list[str] = []
    if body.register_udfs:
        for filename, content in get_lua_modules().items():
            # Add suffix to module name to avoid collisions: aggregation_a3f2b1.lua
            stem = Path(filename).stem
            actual_filename = f"{stem}_{suffix}.lua"
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = str(Path(tmp_dir) / actual_filename)
                Path(tmp_path).write_text(content)
                await client.udf_put(tmp_path)
                udfs_registered.append(actual_filename)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return CreateSampleDataResponse(
        records_created=records_created,
        indexes_created=indexes_created,
        indexes_skipped=indexes_skipped,
        udfs_registered=udfs_registered,
        elapsed_ms=elapsed_ms,
    )

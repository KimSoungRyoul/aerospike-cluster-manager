"""Shared utility functions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from aerospike_cluster_manager_api.models.query import QueryPredicate


def build_predicate(pred: QueryPredicate) -> tuple[object, ...]:
    """Convert a QueryPredicate model into an Aerospike predicate tuple.

    Used by both routers/query.py and routers/records.py.
    """
    from aerospike_py import INDEX_TYPE_LIST, predicates

    op = pred.operator
    if op == "equals":
        return predicates.equals(pred.bin, pred.value)
    if op == "between":
        return predicates.between(pred.bin, pred.value, pred.value2)
    if op == "contains":
        return predicates.contains(pred.bin, INDEX_TYPE_LIST, pred.value)
    if op == "geo_within_region":
        geo = pred.value if isinstance(pred.value, str) else json.dumps(pred.value)
        return predicates.geo_within_geojson_region(pred.bin, geo)
    if op == "geo_contains_point":
        geo = pred.value if isinstance(pred.value, str) else json.dumps(pred.value)
        return predicates.geo_contains_geojson_point(pred.bin, geo)
    raise HTTPException(status_code=400, detail=f"Unknown predicate operator: {op}")


def parse_host_port(host_str: str, default_port: int) -> tuple[str, int]:
    """Parse a host string that may contain an optional ':port' suffix."""
    if ":" in host_str:
        host, port_str = host_str.rsplit(":", 1)
        try:
            return (host, int(port_str))
        except ValueError:
            return (host_str, default_port)
    return (host_str, default_port)


def auto_detect_pk(pk: str) -> str | int:
    """Convert PK to int only when the round-trip is lossless (no leading zeros).

    "1"     -> 1    (integer key)
    "00001" -> "00001"  (string key -- leading zeros preserved)
    "-5"    -> -5   (negative integer key)
    "abc"   -> "abc"  (string key)
    """
    try:
        as_int = int(pk)
        if str(as_int) == pk:
            return as_int
    except ValueError:
        pass
    return pk

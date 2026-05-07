"""Tests for ``mcp/serializers.py``.

Verifies that aerospike-py ``Record`` NamedTuples and bin values of every
supported particle type round-trip into JSON-serialisable Python primitives
fit for embedding in MCP ``text`` / ``json`` content blocks.

Conventions verified:

* ``bytes`` bin values become a marker dict ``{"_aerospike_bytes_b64":
  "<base64>"}`` so a downstream JSON consumer can distinguish a real binary
  blob from a regular string.
* The record key is nested as ``{"namespace", "set", "user_key" | "digest",
  ...}`` — ``digest`` is always populated (base64) for diagnostic clarity;
  ``user_key`` is omitted when the source ``Record`` only carries a digest.
* ``meta`` is nested with ``generation`` and ``expiration`` (mapped from
  aerospike-py ``ttl``); extra ``RecordMetadata`` fields are passed through.
"""

from __future__ import annotations

import base64
import json
from typing import cast

from aerospike_py import Record
from aerospike_py.types import AerospikeKey, RecordMetadata

from aerospike_cluster_manager_api.mcp.serializers import (
    BYTES_MARKER_KEY,
    serialize_bins,
    serialize_record,
    serialize_records,
    serialize_value,
)

# ---------------------------------------------------------------------------
# serialize_value — leaf types
# ---------------------------------------------------------------------------


class TestSerializeValueScalars:
    def test_int(self) -> None:
        assert serialize_value(42) == 42

    def test_negative_int(self) -> None:
        assert serialize_value(-7) == -7

    def test_float(self) -> None:
        assert serialize_value(3.14) == 3.14

    def test_str(self) -> None:
        assert serialize_value("hello") == "hello"

    def test_bool_true(self) -> None:
        # bool is a subclass of int — must remain bool, not coerce to 1.
        result = serialize_value(True)
        assert result is True
        assert isinstance(result, bool)

    def test_bool_false(self) -> None:
        result = serialize_value(False)
        assert result is False
        assert isinstance(result, bool)

    def test_none(self) -> None:
        assert serialize_value(None) is None


class TestSerializeValueBytes:
    def test_bytes_becomes_marker_dict(self) -> None:
        raw = b"\xde\xad\xbe\xef"
        result = serialize_value(raw)
        assert isinstance(result, dict)
        assert set(result.keys()) == {BYTES_MARKER_KEY}
        assert base64.b64decode(result[BYTES_MARKER_KEY]) == raw

    def test_bytearray_becomes_marker_dict(self) -> None:
        raw = bytearray(b"\xca\xfe\xba\xbe")
        result = serialize_value(raw)
        assert isinstance(result, dict)
        assert base64.b64decode(result[BYTES_MARKER_KEY]) == bytes(raw)

    def test_empty_bytes(self) -> None:
        result = serialize_value(b"")
        assert result == {BYTES_MARKER_KEY: ""}

    def test_marker_key_constant_is_namespaced(self) -> None:
        # The marker key must clearly indicate Aerospike-bytes semantics so a
        # human reader and downstream tooling can distinguish from regular
        # JSON. Pin the spelling so we don't break downstream consumers.
        assert BYTES_MARKER_KEY == "_aerospike_bytes_b64"


class TestSerializeValueCollections:
    def test_list_of_ints(self) -> None:
        assert serialize_value([1, 2, 3]) == [1, 2, 3]

    def test_list_of_strings(self) -> None:
        assert serialize_value(["a", "b"]) == ["a", "b"]

    def test_mixed_list(self) -> None:
        assert serialize_value([1, "x", 2.5, True]) == [1, "x", 2.5, True]

    def test_tuple_serialises_to_list(self) -> None:
        # Aerospike CDT does not have tuples, but if a caller passes one we
        # treat it like a list rather than crashing.
        assert serialize_value((1, 2, 3)) == [1, 2, 3]

    def test_empty_list(self) -> None:
        assert serialize_value([]) == []

    def test_nested_list_of_bytes(self) -> None:
        result = serialize_value([b"\x01", b"\x02"])
        assert result == [
            {BYTES_MARKER_KEY: base64.b64encode(b"\x01").decode("ascii")},
            {BYTES_MARKER_KEY: base64.b64encode(b"\x02").decode("ascii")},
        ]

    def test_dict_serialises_to_dict(self) -> None:
        result = serialize_value({"a": 1, "b": "two"})
        assert result == {"a": 1, "b": "two"}

    def test_nested_dict_with_list(self) -> None:
        result = serialize_value({"tags": ["x", "y"], "count": 2})
        assert result == {"tags": ["x", "y"], "count": 2}

    def test_geojson_dict_pass_through(self) -> None:
        # aerospike-py exposes GeoJSON as a plain dict already.
        geo = {"type": "Point", "coordinates": [127.0, 37.5]}
        assert serialize_value(geo) == geo

    def test_deeply_nested(self) -> None:
        value = {
            "outer": [
                {"inner": [1, 2, b"\x00"]},
                {"name": "nested"},
            ]
        }
        result = serialize_value(value)
        assert result == {
            "outer": [
                {"inner": [1, 2, {BYTES_MARKER_KEY: base64.b64encode(b"\x00").decode("ascii")}]},
                {"name": "nested"},
            ]
        }

    def test_dict_with_non_string_keys_coerced(self) -> None:
        # Aerospike maps allow integer keys; JSON does not. We coerce to str
        # so the result is still json.dumps-able.
        result = serialize_value({1: "one", 2: "two"})
        assert result == {"1": "one", "2": "two"}


# ---------------------------------------------------------------------------
# serialize_bins — bin-name keyed dict
# ---------------------------------------------------------------------------


class TestSerializeBins:
    def test_integer_bin(self) -> None:
        assert serialize_bins({"score": 100}) == {"score": 100}

    def test_string_bin(self) -> None:
        assert serialize_bins({"name": "Alice"}) == {"name": "Alice"}

    def test_float_bin(self) -> None:
        assert serialize_bins({"price": 9.99}) == {"price": 9.99}

    def test_bool_bin(self) -> None:
        # Native bool — must stay a bool, not become 1/0.
        result = serialize_bins({"active": True})
        assert result == {"active": True}
        assert isinstance(result["active"], bool)

    def test_list_bin(self) -> None:
        result = serialize_bins({"tags": ["red", "blue"]})
        assert result == {"tags": ["red", "blue"]}

    def test_map_bin(self) -> None:
        result = serialize_bins({"profile": {"first": "A", "last": "B"}})
        assert result == {"profile": {"first": "A", "last": "B"}}

    def test_geojson_bin(self) -> None:
        geo = {"type": "Point", "coordinates": [127.0, 37.5]}
        assert serialize_bins({"location": geo}) == {"location": geo}

    def test_bytes_bin(self) -> None:
        result = serialize_bins({"blob": b"\x00\x01\x02"})
        assert result == {
            "blob": {BYTES_MARKER_KEY: base64.b64encode(b"\x00\x01\x02").decode("ascii")},
        }

    def test_list_with_nested_bytes_bin(self) -> None:
        result = serialize_bins({"chunks": [b"abc", b"def"]})
        assert result == {
            "chunks": [
                {BYTES_MARKER_KEY: base64.b64encode(b"abc").decode("ascii")},
                {BYTES_MARKER_KEY: base64.b64encode(b"def").decode("ascii")},
            ],
        }

    def test_empty_bins(self) -> None:
        assert serialize_bins({}) == {}

    def test_result_is_json_dumpable(self) -> None:
        bins = {
            "i": 1,
            "f": 1.5,
            "s": "x",
            "b": True,
            "lst": [1, "a", b"\x00"],
            "map": {"k": [b"\x01", 2]},
            "geo": {"type": "Point", "coordinates": [1.0, 2.0]},
            "blob": b"binary",
        }
        result = serialize_bins(bins)
        # Must round-trip through json without raising.
        json.dumps(result)


# ---------------------------------------------------------------------------
# serialize_record — full record envelope
# ---------------------------------------------------------------------------


class TestSerializeRecord:
    def test_full_record_with_string_user_key(self) -> None:
        rec = Record(
            key=AerospikeKey("test", "sample_set", "pk-1", b"\xde\xad\xbe\xef"),
            meta=RecordMetadata(gen=3, ttl=86400),
            bins={"name": "Alice", "age": 30, "active": True},
        )

        result = serialize_record(rec)

        assert result["key"]["namespace"] == "test"
        assert result["key"]["set"] == "sample_set"
        assert result["key"]["user_key"] == "pk-1"
        assert result["key"]["digest"] == base64.b64encode(b"\xde\xad\xbe\xef").decode("ascii")
        assert result["meta"]["generation"] == 3
        assert result["meta"]["expiration"] == 86400
        assert result["bins"] == {"name": "Alice", "age": 30, "active": True}

    def test_record_with_int_user_key(self) -> None:
        rec = Record(
            key=AerospikeKey("test", "myset", 42, b"\x01\x02"),
            meta=RecordMetadata(gen=1, ttl=0),
            bins={"score": 100},
        )
        result = serialize_record(rec)
        assert result["key"]["user_key"] == 42
        assert isinstance(result["key"]["user_key"], int)

    def test_record_with_bytes_user_key_uses_marker(self) -> None:
        rec = Record(
            key=AerospikeKey("test", "myset", b"\xca\xfe", b"\x00\xff"),
            meta=RecordMetadata(gen=1, ttl=0),
            bins={},
        )
        result = serialize_record(rec)
        assert result["key"]["user_key"] == {
            BYTES_MARKER_KEY: base64.b64encode(b"\xca\xfe").decode("ascii"),
        }

    def test_record_with_none_user_key_omits_user_key(self) -> None:
        # Digest-only record (no user_key persisted): expose digest, not user_key.
        rec = Record(
            key=AerospikeKey("test", "myset", None, b"\x00\x11\x22\x33"),
            meta=RecordMetadata(gen=1, ttl=0),
            bins={},
        )
        result = serialize_record(rec)
        assert "user_key" not in result["key"]
        assert result["key"]["digest"] == base64.b64encode(b"\x00\x11\x22\x33").decode("ascii")

    def test_record_with_bytearray_digest(self) -> None:
        # Aerospike-py types ``digest`` as bytes, but bytearray flows through
        # the same isinstance() check; cast at the call site so pyright is
        # happy without losing test coverage of the bytearray branch.
        digest = cast("bytes", bytearray(b"\xab\xcd"))
        rec = Record(
            key=AerospikeKey("test", "myset", "pk-1", digest),
            meta=RecordMetadata(gen=1, ttl=0),
            bins={},
        )
        result = serialize_record(rec)
        assert result["key"]["digest"] == base64.b64encode(b"\xab\xcd").decode("ascii")

    def test_record_with_dict_meta(self) -> None:
        # Some aerospike-py paths still surface meta as a dict; the type
        # annotation now says RecordMetadata only, so cast for type-checker.
        meta = cast("RecordMetadata", {"gen": 2, "ttl": 500, "last_update_time": 1234567})
        rec = Record(
            key=AerospikeKey("test", "myset", "pk", b"\x00"),
            meta=meta,
            bins={"x": 1},
        )
        result = serialize_record(rec)
        assert result["meta"]["generation"] == 2
        assert result["meta"]["expiration"] == 500
        # Extra dict keys flow through so MCP clients can read them.
        assert result["meta"]["last_update_time"] == 1234567

    def test_record_with_none_meta_defaults(self) -> None:
        rec = Record(
            key=AerospikeKey("test", "myset", "pk", b"\x00"),
            meta=None,
            bins={"x": 1},
        )
        result = serialize_record(rec)
        assert result["meta"]["generation"] == 0
        assert result["meta"]["expiration"] == 0

    def test_record_with_none_bins_becomes_empty_dict(self) -> None:
        rec = Record(
            key=AerospikeKey("test", "myset", "pk", b"\x00"),
            meta=RecordMetadata(gen=1, ttl=0),
            bins=None,
        )
        result = serialize_record(rec)
        assert result["bins"] == {}

    def test_record_with_complex_bins(self) -> None:
        rec = Record(
            key=AerospikeKey("test", "myset", "pk", b"\x00"),
            meta=RecordMetadata(gen=1, ttl=0),
            bins={
                "tags": ["python", b"\x01\x02"],
                "metadata": {"source": "import", "version": 2},
                "location": {"type": "Point", "coordinates": [127.0, 37.5]},
                "blob": b"binary",
                "score": 3.14,
            },
        )

        result = serialize_record(rec)

        assert result["bins"]["tags"][0] == "python"
        assert result["bins"]["tags"][1] == {
            BYTES_MARKER_KEY: base64.b64encode(b"\x01\x02").decode("ascii"),
        }
        assert result["bins"]["metadata"] == {"source": "import", "version": 2}
        assert result["bins"]["location"] == {"type": "Point", "coordinates": [127.0, 37.5]}
        assert result["bins"]["blob"] == {
            BYTES_MARKER_KEY: base64.b64encode(b"binary").decode("ascii"),
        }
        # round-trip JSON
        json.dumps(result)

    def test_record_no_digest_in_key_tuple(self) -> None:
        # Key tuple without digest — still serialises, digest field is None.
        # Cast required because AerospikeKey is a 4-tuple at the type level
        # but the serializer must tolerate shorter tuples at runtime (some
        # info paths surface namespace-only or 3-tuple keys).
        partial_key = cast("AerospikeKey", ("test", "myset", "pk-1"))
        rec = Record(
            key=partial_key,
            meta=RecordMetadata(gen=1, ttl=0),
            bins={},
        )
        result = serialize_record(rec)
        assert result["key"]["namespace"] == "test"
        assert result["key"]["set"] == "myset"
        assert result["key"]["user_key"] == "pk-1"
        assert result["key"]["digest"] is None


# ---------------------------------------------------------------------------
# serialize_records — bulk
# ---------------------------------------------------------------------------


class TestSerializeRecords:
    def test_empty_iterable(self) -> None:
        assert serialize_records([]) == []

    def test_multiple_records(self) -> None:
        records = [
            Record(
                key=AerospikeKey("test", "s", "pk-1", b"\x01"),
                meta=RecordMetadata(gen=1, ttl=0),
                bins={"a": 1},
            ),
            Record(
                key=AerospikeKey("test", "s", "pk-2", b"\x02"),
                meta=RecordMetadata(gen=2, ttl=10),
                bins={"a": 2},
            ),
        ]

        result = serialize_records(records)

        assert len(result) == 2
        assert result[0]["key"]["user_key"] == "pk-1"
        assert result[1]["key"]["user_key"] == "pk-2"
        assert result[0]["bins"] == {"a": 1}
        assert result[1]["meta"]["generation"] == 2

    def test_accepts_generator(self) -> None:
        def gen():
            yield Record(
                key=AerospikeKey("test", "s", "pk", b"\x00"),
                meta=RecordMetadata(gen=1, ttl=0),
                bins={"x": 1},
            )

        result = serialize_records(gen())
        assert len(result) == 1
        assert result[0]["bins"] == {"x": 1}

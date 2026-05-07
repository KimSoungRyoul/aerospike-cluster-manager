"""Unit tests for the read-only asinfo verb whitelist domain module.

Covers:

* :func:`extract_verb` parsing of the three asinfo command shapes
  (bare, ``:``-args, ``/``-path).
* :func:`assert_read_only` allow / block decisions for every verb in the
  whitelist plus a representative set of write / unknown verbs. The
  parametrized "all whitelisted verbs pass" test is the regression net
  that catches accidental whitelist trims.
"""

from __future__ import annotations

import pytest

from aerospike_cluster_manager_api.info_verbs import (
    READ_ONLY_INFO_VERBS,
    InfoVerbNotAllowed,
    assert_read_only,
    extract_verb,
)


class TestExtractVerb:
    def test_bare_verb(self) -> None:
        assert extract_verb("namespaces") == "namespaces"

    def test_colon_args(self) -> None:
        assert extract_verb("roster:namespace=test") == "roster"

    def test_colon_multi_args(self) -> None:
        assert extract_verb("latencies:back=10;duration=10") == "latencies"

    def test_slash_path(self) -> None:
        assert extract_verb("sets/test/myset") == "sets"

    def test_slash_namespace(self) -> None:
        assert extract_verb("namespace/test") == "namespace"

    def test_xdr_dc_with_args(self) -> None:
        assert extract_verb("xdr-dc:dc=DC1") == "xdr-dc"

    def test_leading_trailing_whitespace(self) -> None:
        assert extract_verb("  version  ") == "version"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InfoVerbNotAllowed) as exc:
            extract_verb("")
        assert exc.value.verb == ""

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InfoVerbNotAllowed) as exc:
            extract_verb("   \t\n  ")
        assert exc.value.verb == ""


class TestAssertReadOnly:
    @pytest.mark.parametrize("verb", sorted(READ_ONLY_INFO_VERBS))
    def test_every_whitelisted_verb_passes(self, verb: str) -> None:
        # Bare-form must pass for every whitelisted verb. This is the
        # regression net for accidental trims to READ_ONLY_INFO_VERBS.
        assert_read_only(verb)

    def test_whitelist_membership_is_pinned(self) -> None:
        """Force a deliberate decision when adding/removing a verb.

        The expected set is duplicated here on purpose so silent ADDITIONS
        to ``READ_ONLY_INFO_VERBS`` (e.g. a refactor accidentally including
        a write verb) fail loudly here rather than passing the parametrized
        ``test_every_whitelisted_verb_passes`` (which fans out per-member
        and would simply add one more green test for a dangerous addition).
        """
        expected = frozenset(
            {
                # Cluster meta (8)
                "version",
                "build",
                "build-os",
                "build-time",
                "node",
                "service",
                "services",
                "services-alumni",
                # Cluster topology / health (7)
                "nodes",
                "cluster-name",
                "cluster-stable",
                "cluster-generation",
                "cluster-info",
                "health-outliers",
                "health-stats",
                # Namespace / set / index (4)
                "namespaces",
                "namespace",
                "sets",
                "sindex",
                # Stats (3)
                "statistics",
                "latencies",
                "udf-list",
                # Strong-consistency / rack (2)
                "roster",
                "racks",
            }
        )
        assert expected == READ_ONLY_INFO_VERBS
        assert len(READ_ONLY_INFO_VERBS) == 24

    def test_colon_args_pass_when_verb_whitelisted(self) -> None:
        assert_read_only("roster:namespace=test")
        assert_read_only("latencies:back=10")
        assert_read_only("namespace:test")

    def test_trailing_semicolon_accepted(self) -> None:
        # ``namespaces;`` is the canonical asinfo CLI form when piping
        # multiple commands. The verb extractor strips the trailing ``;``
        # so the LLM-friendly form passes the whitelist.
        assert assert_read_only("namespaces;") == "namespaces"
        assert assert_read_only("version;") == "version"

    def test_assert_returns_parsed_verb(self) -> None:
        # Forward-compat for telemetry — callers can attach the parsed
        # verb to OTel span attributes / structured logs.
        assert assert_read_only("roster:namespace=test") == "roster"
        assert assert_read_only("sets/test/myset") == "sets"

    def test_slash_path_pass_when_verb_whitelisted(self) -> None:
        assert_read_only("sets/test/myset")
        assert_read_only("namespace/test")
        assert_read_only("sindex/test/idx_name")

    @pytest.mark.parametrize(
        "command",
        [
            "set-config:context=service;migrate-threads=2",
            "truncate-namespace:namespace=test",
            "recluster:",
            "set-roster:namespace=test;nodes=ABCD,EFGH",
            "create-roster:",
            "quiesces",
            "quiesce-undo",
            "sindex-create:ns=test;set=demo",
            "sindex-delete:ns=test;indexname=foo",
        ],
    )
    def test_known_writes_blocked(self, command: str) -> None:
        with pytest.raises(InfoVerbNotAllowed):
            assert_read_only(command)

    @pytest.mark.parametrize(
        "command",
        [
            "frobnicate",
            "Namespaces",  # case-sensitive — capital N is rejected
            "VERSION",
            "dump-fabric:",  # debug dumps deliberately excluded
            "dump-msgs:",
            "eviction",  # excluded conservatively
            "bins",  # deprecated since Aerospike 7.0, removal in 9.x
            "bins/test",
            "xdr-dc",  # XDR not available on CE
            "dc:dc=DC1",  # XDR not available on CE
        ],
    )
    def test_unknown_or_excluded_verb_blocked(self, command: str) -> None:
        with pytest.raises(InfoVerbNotAllowed):
            assert_read_only(command)

    def test_empty_command_blocked(self) -> None:
        with pytest.raises(InfoVerbNotAllowed):
            assert_read_only("")

    def test_error_carries_extracted_verb(self) -> None:
        with pytest.raises(InfoVerbNotAllowed) as exc:
            assert_read_only("recluster:")
        assert exc.value.verb == "recluster"

    def test_error_message_mentions_a_few_allowed_verbs(self) -> None:
        # The wire message points the LLM at the allowed list in lieu of
        # a separate "list allowed verbs" tool. Exact wording is not
        # asserted — just the shape.
        with pytest.raises(InfoVerbNotAllowed) as exc:
            assert_read_only("frobnicate")
        msg = str(exc.value)
        assert "frobnicate" in msg
        assert "execute_info" in msg

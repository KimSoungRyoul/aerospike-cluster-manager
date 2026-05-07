"""Read-only asinfo verb whitelist for ``ACM_MCP_ACCESS_PROFILE=read_only``.

The Aerospike asinfo protocol multiplexes both reads (``namespaces``,
``version``, ``roster:``, ...) and writes (``set-config:``, ``recluster:``,
``truncate-namespace:``) over the same wire format. The MCP read-only
profile therefore cannot decide a tool's safety from its name alone — it
needs to inspect the *verb* (the leading token of the command).

This module is the single source of truth for that decision. It lives at
the package root so the service layer can import it without reaching back
into ``mcp/``; the service raises :class:`InfoVerbNotAllowed`, the MCP
error mapper at :mod:`mcp.errors` translates it to ``code=invalid_argument``.

To add a verb:

1. Verify in the Aerospike CE 8.1 docs that the verb is purely read-only
   and triggers no persistent state change (no log dump, no metric
   counter mutation beyond standard read paths).
2. Add it to :data:`READ_ONLY_INFO_VERBS` below in the matching category.
3. Add a unit test in ``tests/test_info_verbs.py`` so future drift is caught.
"""

from __future__ import annotations

READ_ONLY_INFO_VERBS: frozenset[str] = frozenset(
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
        # Namespace / set / index (5)
        "namespaces",
        "namespace",
        "sets",
        "bins",
        "sindex",
        # Stats (3)
        "statistics",
        "latencies",
        "udf-list",
        # Strong-consistency / rack / XDR (4)
        "roster",
        "racks",
        "xdr-dc",
        "dc",
    }
)


class InfoVerbNotAllowed(ValueError):
    """Raised when an asinfo command's leading verb is not on the read-only allowlist.

    The MCP error mapper translates this to
    :class:`mcp.errors.MCPToolError` with ``code="invalid_argument"`` so
    LLM clients receive a "pick a different verb" signal rather than a
    permission denial.
    """

    def __init__(self, verb: str) -> None:
        # Five-verb hint keeps the wire message short; the full list lives
        # in the tool docstring and the MCP JSON schema description.
        sample = ", ".join(sorted(READ_ONLY_INFO_VERBS)[:5])
        super().__init__(
            f"Verb {verb!r} is not on the read-only asinfo whitelist; "
            f"pick from: {sample}, ... or use execute_info under "
            f"ACM_MCP_ACCESS_PROFILE=full."
        )
        self.verb = verb


def extract_verb(command: str) -> str:
    """Return the leading verb of an asinfo command.

    asinfo commands take three syntactic shapes:

    * bare verb — ``"namespaces"``
    * path-style — ``"sets/test/myset"`` (verb followed by ``/``-separated args)
    * colon-style — ``"roster:namespace=test"`` (verb followed by ``:`` and
      ``;``-separated key=value args)

    We split on the *first* ``:`` then on the *first* ``/`` so both styles
    yield the verb in the head position. Whitespace is trimmed; an empty
    or whitespace-only command raises :class:`InfoVerbNotAllowed` with an
    empty verb so the caller surfaces a sensible error.

    Note: case-sensitive — asinfo itself is case-sensitive
    (``Namespaces`` is not the same verb as ``namespaces``).
    """
    cmd = command.strip()
    if not cmd:
        raise InfoVerbNotAllowed("")
    return cmd.split(":", 1)[0].split("/", 1)[0]


def assert_read_only(command: str) -> None:
    """Raise :class:`InfoVerbNotAllowed` if ``command``'s verb is not whitelisted.

    Returns ``None`` on success — callers should run the command immediately
    after this returns.
    """
    verb = extract_verb(command)
    if verb not in READ_ONLY_INFO_VERBS:
        raise InfoVerbNotAllowed(verb)

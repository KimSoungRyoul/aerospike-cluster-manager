"""Smoke tests for the empty MCP server factory.

Task A.6 only verifies that ``build_mcp_app`` returns a ``FastMCP``
instance whose ``name`` is ``aerospike-cluster-manager``. Tool
registration, transport mounting and HTTP-level checks come in later
tasks (A.7+ and B.*).
"""

from mcp.server.fastmcp import FastMCP

from aerospike_cluster_manager_api.mcp.server import build_mcp_app


def test_build_returns_fastmcp_named_acm() -> None:
    mcp = build_mcp_app()
    assert isinstance(mcp, FastMCP)
    assert mcp.name == "aerospike-cluster-manager"

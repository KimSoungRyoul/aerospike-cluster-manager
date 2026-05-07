"""ACM MCP server factory.

Builds an empty :class:`FastMCP` instance. Tools, lifespan, and
transport mounting are wired in later tasks (A.7+).
"""

from mcp.server.fastmcp import FastMCP


def build_mcp_app() -> FastMCP:
    """Construct the ACM MCP server. Tools registered in later tasks."""
    return FastMCP("aerospike-cluster-manager")

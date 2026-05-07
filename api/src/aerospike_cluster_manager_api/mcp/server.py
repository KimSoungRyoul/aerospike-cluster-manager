"""ACM MCP server factory.

Builds the :class:`FastMCP` instance, imports each tools submodule (which
runs the ``@tool(...)`` decorators at import time), then flushes the
registry into the FastMCP app.
"""

from mcp.server.fastmcp import FastMCP

from aerospike_cluster_manager_api.mcp import tools  # noqa: F401  — import side-effects only
from aerospike_cluster_manager_api.mcp.registry import register_all


def build_mcp_app() -> FastMCP:
    """Construct the ACM MCP server with all decorated tools registered.

    ``streamable_http_path="/"`` keeps the inner Streamable-HTTP route at
    the root of the FastMCP sub-app, so when ``main.py`` mounts the sub-app
    at ``/mcp`` (``ACM_MCP_PATH``) clients can reach the transport at
    exactly ``/mcp`` rather than the doubled ``/mcp/mcp`` produced by the
    SDK default.
    """
    mcp = FastMCP("aerospike-cluster-manager", streamable_http_path="/")
    register_all(mcp)
    return mcp

"""MCP tool modules.

Each submodule registers its tools at import time via the ``@tool(...)``
decorator from :mod:`aerospike_cluster_manager_api.mcp.registry`. The
auto-discovery wiring imports each submodule so the decorator
side-effects fire before :func:`register_all` flushes the accumulator
into the :class:`FastMCP` instance built by :func:`build_mcp_app`.

Adding a new tool category? Import the module here AND keep
``access_profile.WRITE_TOOLS`` in sync with any new mutation tools.
"""

from aerospike_cluster_manager_api.mcp.tools import (  # noqa: F401  — import side-effects only
    cluster_info,
    connections,
    info_commands,
    query,
    records,
)

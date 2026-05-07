"""MCP tool modules.

Each submodule registers its tools at import time via the ``@tool(...)``
decorator from :mod:`aerospike_cluster_manager_api.mcp.registry`. The
auto-discovery wiring in B.6 imports each submodule so the decorator
side-effects fire before :func:`register_all` flushes the accumulator
into the :class:`FastMCP` instance built by :func:`build_mcp_app`.
"""

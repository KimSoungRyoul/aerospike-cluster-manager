"""MCP bearer-token middleware (OIDC-OR-bearer).

The middleware sits in front of the MCP mount and applies an
OR-combined gate with the existing OIDC middleware:

* It runs ONLY on requests whose ``url.path`` begins with
  ``config.ACM_MCP_PATH`` (default ``/mcp``). Non-MCP paths are
  passed through unchanged regardless of token settings.

* If ``ACM_MCP_TOKEN`` is unset, the middleware delegates entirely
  to OIDC — it does not 401 on its own. This is the production
  default for deployments that secure the MCP surface via the same
  Keycloak realm as the REST API.

* If ``ACM_MCP_TOKEN`` is set, the request passes when EITHER:
    - OIDC has already authenticated the request (i.e.
      ``request.state.user`` is non-None), OR
    - The ``Authorization`` header carries a matching
      ``Bearer <token>`` value.
  Otherwise the middleware returns ``401 {"detail": "MCP authentication
  required"}``.

Token comparison uses :func:`secrets.compare_digest` so the wall-clock
cost is independent of the prefix match length — which closes a timing
side-channel in naive ``==`` comparisons. The configured and supplied
tokens are NEVER logged.

Wiring lives in :mod:`aerospike_cluster_manager_api.main`. The
middleware is installed only when ``ACM_MCP_ENABLED=true``; when that
flag is false the MCP mount itself does not exist, so installing the
middleware would be dead weight.
"""

from __future__ import annotations

import logging
import secrets

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aerospike_cluster_manager_api import config

logger = logging.getLogger(__name__)


_UNAUTHORIZED_BODY: dict[str, str] = {"detail": "MCP authentication required"}


class MCPBearerTokenMiddleware(BaseHTTPMiddleware):
    """Bearer-token gate for the ``/mcp/*`` mount.

    See module docstring for the full truth table. This class
    intentionally has no ``__init__`` overrides — all knobs come from
    :mod:`aerospike_cluster_manager_api.config` and are read at
    request time, so test code can monkeypatch + ``importlib.reload``
    the config module without re-instantiating the middleware.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Read path-prefix from config at request time so deployments
        # that override ACM_MCP_PATH still gate correctly.
        if not request.url.path.startswith(config.ACM_MCP_PATH):
            return await call_next(request)

        token = config.ACM_MCP_TOKEN
        if not token:
            # No MCP-specific token configured. Defer to OIDC, which
            # runs unconditionally on all paths in main.py's middleware
            # stack. If OIDC is also disabled, the request is anonymous
            # — that's the operator's choice.
            return await call_next(request)

        # OR-leg #1: already authenticated via OIDC. The OIDC middleware
        # writes ``request.state.user_claims`` on success.
        if getattr(request.state, "user_claims", None) is not None:
            return await call_next(request)

        # OR-leg #2: bearer header matches the configured token.
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            logger.warning(
                "MCP request rejected: missing or non-bearer Authorization header (path=%s)",
                request.url.path,
            )
            return JSONResponse(_UNAUTHORIZED_BODY, status_code=401)

        # ``split(" ", 1)`` after the lower-case prefix check above is
        # safe because the header is known to start with ``bearer <space>``.
        supplied = header.split(" ", 1)[1].strip()
        if not supplied or not secrets.compare_digest(supplied, token):
            # Do NOT log the supplied or configured token — this branch
            # is the most likely to leak secrets if a future maintainer
            # adds debug logging carelessly.
            logger.warning(
                "MCP request rejected: bearer token mismatch (path=%s)",
                request.url.path,
            )
            return JSONResponse(_UNAUTHORIZED_BODY, status_code=401)

        return await call_next(request)

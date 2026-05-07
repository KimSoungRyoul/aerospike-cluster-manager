"""MCP bearer-token middleware (OIDC-OR-bearer).

The middleware sits in front of the MCP mount and applies an
OR-combined gate with the existing OIDC middleware. It is installed
OUTSIDE OIDC at request time (added LAST in main.py) so the bearer
leg runs first and can short-circuit past OIDC.

* It runs ONLY on requests whose ``url.path`` begins with
  ``config.ACM_MCP_PATH`` (default ``/mcp``). Non-MCP paths are
  passed through unchanged regardless of token settings. Path matching
  is on segment boundaries (exact match or ``base + "/"``) so a route
  named ``/mcp-evil/...`` cannot impersonate the MCP surface.

* If ``ACM_MCP_TOKEN`` is unset, the middleware delegates entirely
  to OIDC — it does not 401 on its own. This is the production
  default for deployments that secure the MCP surface via the same
  Keycloak realm as the REST API.

* If ``ACM_MCP_TOKEN`` is set:
    - Bearer matches the configured token → set a sentinel
      ``request.state.user_claims = {"sub": "mcp-bearer", ...}`` so
      :class:`OIDCAuthMiddleware` defers, and pass through.
    - Bearer mismatch (or no Authorization header) and OIDC is
      enabled → fall through to OIDC, which will authenticate the
      request as a JWT or 401 itself (the OR semantic).
    - Bearer mismatch (or no Authorization header) and OIDC is
      disabled → 401 ``{"detail": "MCP authentication required"}``
      with a ``WWW-Authenticate: Bearer realm="acm-mcp"`` header so
      RFC-7235-compliant clients know the challenge scheme.

Token comparison uses :func:`secrets.compare_digest` so the wall-clock
cost is independent of the prefix match length — which closes a timing
side-channel in naive ``==`` comparisons. Inputs are UTF-8-encoded
inside a try/except so a hostile or malformed header (non-ASCII bytes,
encoding errors) can never crash the middleware; any failure is
treated as auth failure. The configured and supplied tokens are NEVER
logged.

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
_UNAUTHORIZED_HEADERS: dict[str, str] = {"WWW-Authenticate": 'Bearer realm="acm-mcp"'}


def _unauthorized() -> JSONResponse:
    """Build the canonical 401 response for the MCP gate.

    Centralized so both call sites (missing/non-bearer header and
    bearer token mismatch) emit the same body AND the same
    ``WWW-Authenticate`` challenge header (M4).
    """
    return JSONResponse(_UNAUTHORIZED_BODY, status_code=401, headers=_UNAUTHORIZED_HEADERS)


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
        # that override ACM_MCP_PATH still gate correctly. We compare on
        # path-segment boundaries (M1): exact match against ``base`` OR
        # path begins with ``base + "/"``. A naive ``startswith(base)``
        # would let ``/mcp-evil/foo`` slip past the gate when
        # ACM_MCP_PATH is ``/mcp``.
        path = request.url.path
        base = config.ACM_MCP_PATH
        if path != base and not path.startswith(base.rstrip("/") + "/"):
            return await call_next(request)

        token = config.ACM_MCP_TOKEN
        if not token:
            # No MCP-specific token configured. Defer to OIDC, which
            # runs unconditionally on all paths in main.py's middleware
            # stack. If OIDC is also disabled, the request is anonymous
            # — that's the operator's choice.
            return await call_next(request)

        # OR-leg #1: already authenticated upstream (rare — usually
        # OIDC runs INNER to this middleware, but a future stack might
        # add another auth layer outside us).
        if getattr(request.state, "user_claims", None) is not None:
            return await call_next(request)

        # OR-leg #2: bearer header matches the configured token.
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            # ``split(" ", 1)`` after the lower-case prefix check above is
            # safe because the header is known to start with ``bearer <space>``.
            supplied = header.split(" ", 1)[1].strip()
            # ``secrets.compare_digest`` raises TypeError on non-ASCII ``str``
            # inputs (e.g. ``Bearer café``). Encode to UTF-8 bytes inside a
            # try/except so a hostile or malformed header can never crash the
            # middleware — any encoding error is treated as auth failure (B1).
            try:
                ok = bool(supplied) and secrets.compare_digest(supplied.encode("utf-8"), token.encode("utf-8"))
            except Exception:
                ok = False
            if ok:
                # Bearer matches — set a sentinel claim so the inner
                # OIDCAuthMiddleware defers (it short-circuits when
                # user_claims is already populated) and the request
                # reaches the MCP mount without OIDC trying to verify
                # an opaque token as a JWT.
                request.state.user_claims = {"sub": "mcp-bearer", "_mcp_bearer": True}
                return await call_next(request)
            # Bearer-shaped header but mismatch. If OIDC is enabled,
            # give it a chance to verify the header as a JWT (the
            # OIDC-OR-bearer semantic). If OIDC is disabled, we are the
            # only gate, so 401.
            if not config.OIDC_ENABLED:
                # Do NOT log the supplied or configured token — this branch
                # is the most likely to leak secrets if a future maintainer
                # adds debug logging carelessly.
                logger.warning(
                    "MCP request rejected: bearer token mismatch (path=%s)",
                    request.url.path,
                )
                return _unauthorized()
            # OIDC will run next; let it try (or 401 itself).
            return await call_next(request)

        # No bearer-shaped Authorization header. Fall through to OIDC if
        # enabled; otherwise 401 — there is no other auth gate.
        if config.OIDC_ENABLED:
            return await call_next(request)
        logger.warning(
            "MCP request rejected: missing or non-bearer Authorization header (path=%s)",
            request.url.path,
        )
        return _unauthorized()

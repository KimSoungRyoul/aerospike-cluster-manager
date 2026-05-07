"""Tests for the MCP bearer-token middleware.

The middleware sits in front of the MCP mount and applies an
OR-combined gate with the existing OIDC middleware:

* Pre-conditions:
  - It runs ONLY on requests whose ``url.path`` begins with
    ``config.ACM_MCP_PATH`` (default ``/mcp``).
  - It is installed only when ``ACM_MCP_ENABLED=true`` (the mount
    itself is also gated by that flag).

* Truth table when ``ACM_MCP_TOKEN`` is set:

    | OIDC says authenticated | Bearer matches token | Result |
    |-------------------------|----------------------|--------|
    | yes                     | n/a                  | pass   |
    | no                      | yes                  | pass   |
    | no                      | no / missing         | 401    |

* When ``ACM_MCP_TOKEN`` is unset, the middleware is a pass-through
  and defers entirely to the existing OIDC middleware.

Tests build a tiny FastAPI app, install the middleware directly, and
probe it via :class:`httpx.ASGITransport` — no uvicorn, no real
network. A separate group of tests exercises the conditional
installation in :mod:`aerospike_cluster_manager_api.main` via the
same ``importlib.reload`` pattern that ``test_main_mount.py`` uses.
"""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(
    *,
    install_oidc_stub: bool = False,
    oidc_authenticated: bool = False,
) -> FastAPI:
    """Construct an app that mirrors the real /mcp + /api shape.

    The MCP middleware is installed by the test using
    ``app.add_middleware(MCPBearerTokenMiddleware)`` — same call site as
    ``main.py``. When ``install_oidc_stub`` is true an additional
    middleware is wired up that simulates OIDC by setting
    ``request.state.user_claims`` to a dummy claim dict on every request — this
    lets us exercise the OIDC-OR-bearer leg without spinning up a real
    JWKS server.
    """
    from aerospike_cluster_manager_api.mcp.auth import MCPBearerTokenMiddleware

    app = FastAPI()

    @app.get("/mcp")
    async def mcp_root() -> dict:
        return {"ok": True}

    @app.get("/mcp/sub/path")
    async def mcp_sub() -> dict:
        return {"ok": True}

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    # MCP middleware first (installed before OIDC stub so it runs AFTER
    # the OIDC stub at request time — Starlette runs middleware in
    # reverse order of add_middleware).
    app.add_middleware(MCPBearerTokenMiddleware)

    if install_oidc_stub:
        # Tiny OIDC stand-in: writes ``request.state.user_claims`` so the
        # MCP middleware sees an authenticated request without us having
        # to mint real JWTs. (Matches the attribute name set by the real
        # ``OIDCAuthMiddleware`` in ``middleware/oidc_auth.py``.)
        class _OIDCStub(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                if oidc_authenticated:
                    request.state.user_claims = {"sub": "stub-user"}
                return await call_next(request)

        app.add_middleware(_OIDCStub)

    return app


def _reload_config(monkeypatch: pytest.MonkeyPatch, **env: str | None) -> None:
    """Set/unset env vars and reload the config module so module-level
    constants re-evaluate against the patched environment.

    Pass ``key=None`` to unset.
    """
    from aerospike_cluster_manager_api import config as _config

    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    importlib.reload(_config)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_acm_mcp_token_defaults_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the env var set, ``ACM_MCP_TOKEN`` is the empty string."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN=None)
    from aerospike_cluster_manager_api import config as _config

    try:
        assert _config.ACM_MCP_TOKEN == ""
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


def test_acm_mcp_token_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="s3cret")
    from aerospike_cluster_manager_api import config as _config

    try:
        assert _config.ACM_MCP_TOKEN == "s3cret"
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


# ---------------------------------------------------------------------------
# Direct middleware tests — token UNSET (delegates to OIDC)
# ---------------------------------------------------------------------------


async def test_token_unset_passes_through_on_mcp_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``ACM_MCP_TOKEN`` is unset, /mcp requests pass through to the
    next layer without enforcement (this leg defers to OIDC)."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN=None)
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/mcp")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_token_unset_does_not_touch_non_mcp_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN=None)
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


# ---------------------------------------------------------------------------
# Direct middleware tests — token SET, no OIDC
# ---------------------------------------------------------------------------


async def test_correct_bearer_token_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/mcp", headers={"Authorization": "Bearer correct-token"})
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_correct_bearer_token_passes_on_subpath(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/mcp/sub/path",
                headers={"Authorization": "Bearer correct-token"},
            )
            assert resp.status_code == 200
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_missing_authorization_header_yields_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/mcp")
            assert resp.status_code == 401
            assert resp.json() == {"detail": "MCP authentication required"}
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_wrong_bearer_token_yields_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/mcp", headers={"Authorization": "Bearer wrong-token"})
            assert resp.status_code == 401
            assert resp.json() == {"detail": "MCP authentication required"}
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_non_bearer_scheme_yields_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Basic auth must not satisfy a bearer gate even if the
            # base64 payload happens to equal the token bytes.
            resp = await ac.get("/mcp", headers={"Authorization": "Basic correct-token"})
            assert resp.status_code == 401
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_bearer_scheme_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    """RFC 7235 — auth scheme matching is case-insensitive."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/mcp", headers={"Authorization": "bearer correct-token"})
            assert resp.status_code == 200
            resp = await ac.get("/mcp", headers={"Authorization": "BEARER correct-token"})
            assert resp.status_code == 200
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


# ---------------------------------------------------------------------------
# Direct middleware tests — token SET, OIDC-OR-bearer
# ---------------------------------------------------------------------------


async def test_oidc_authenticated_passes_even_with_wrong_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If OIDC has authenticated the request (request.state.user_claims set),
    the bearer header is ignored — OIDC alone is enough."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app(install_oidc_stub=True, oidc_authenticated=True)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Wrong bearer, but OIDC said yes → pass
            resp = await ac.get("/mcp", headers={"Authorization": "Bearer wrong-token"})
            assert resp.status_code == 200
            # No bearer header at all, but OIDC said yes → pass
            resp = await ac.get("/mcp")
            assert resp.status_code == 200
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_oidc_anonymous_and_wrong_bearer_yields_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If OIDC did NOT authenticate the request and the bearer is wrong/
    missing, both legs of the OR fail and the middleware returns 401."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app(install_oidc_stub=True, oidc_authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/mcp", headers={"Authorization": "Bearer wrong-token"})
            assert resp.status_code == 401
            assert resp.json() == {"detail": "MCP authentication required"}
            resp = await ac.get("/mcp")
            assert resp.status_code == 401
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_oidc_anonymous_and_correct_bearer_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app(install_oidc_stub=True, oidc_authenticated=False)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(
                "/mcp",
                headers={"Authorization": "Bearer correct-token"},
            )
            assert resp.status_code == 200
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


# ---------------------------------------------------------------------------
# Path-prefix gating
# ---------------------------------------------------------------------------


async def test_non_mcp_path_is_never_touched_when_token_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with ``ACM_MCP_TOKEN`` configured, paths outside ``/mcp/*``
    are not gated by this middleware."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


async def test_custom_mcp_path_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """The middleware reads ``config.ACM_MCP_PATH`` at request time, so an
    operator override is respected."""
    _reload_config(
        monkeypatch,
        ACM_MCP_TOKEN="correct-token",
        ACM_MCP_PATH="/agents/mcp",
    )
    try:
        from aerospike_cluster_manager_api.mcp.auth import MCPBearerTokenMiddleware

        app = FastAPI()

        @app.get("/agents/mcp")
        async def custom_mcp() -> dict:
            return {"ok": True}

        @app.get("/api/health")
        async def health() -> dict:
            return {"status": "ok"}

        app.add_middleware(MCPBearerTokenMiddleware)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Custom path: gated.
            resp = await ac.get("/agents/mcp")
            assert resp.status_code == 401
            resp = await ac.get(
                "/agents/mcp",
                headers={"Authorization": "Bearer correct-token"},
            )
            assert resp.status_code == 200
            # Non-MCP path: untouched.
            resp = await ac.get("/api/health")
            assert resp.status_code == 200
            # Default ``/mcp`` is NOT a match because the override is in effect.
            resp = await ac.get("/mcp")
            assert resp.status_code == 404
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None, ACM_MCP_PATH=None)


# ---------------------------------------------------------------------------
# Token never appears in logs
# ---------------------------------------------------------------------------


async def test_token_never_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A wrong-bearer 401 must not echo the supplied token in any log line."""
    _reload_config(monkeypatch, ACM_MCP_TOKEN="correct-token")
    try:
        # Capture WARNING+ from anywhere in our package.
        caplog.set_level("DEBUG", logger="aerospike_cluster_manager_api")
        app = _build_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.get(
                "/mcp",
                headers={"Authorization": "Bearer leaked-supplied-token"},
            )
        log_text = "\n".join(record.getMessage() for record in caplog.records)
        assert "leaked-supplied-token" not in log_text, f"supplied token leaked into logs: {log_text!r}"
        assert "correct-token" not in log_text, f"configured token leaked into logs: {log_text!r}"
    finally:
        _reload_config(monkeypatch, ACM_MCP_TOKEN=None)


# ---------------------------------------------------------------------------
# main.py wiring — middleware installed only when ACM_MCP_ENABLED=true
# ---------------------------------------------------------------------------


@pytest.fixture()
async def app_with_mcp_enabled_and_token(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[object]:
    """Reload main with ACM_MCP_ENABLED=true and a known token."""
    monkeypatch.setenv("ACM_MCP_ENABLED", "true")
    monkeypatch.setenv("ACM_MCP_TOKEN", "wired-token")
    from aerospike_cluster_manager_api import config as _config
    from aerospike_cluster_manager_api import main as _main

    importlib.reload(_config)
    importlib.reload(_main)
    try:
        yield _main.app
    finally:
        monkeypatch.delenv("ACM_MCP_ENABLED", raising=False)
        monkeypatch.delenv("ACM_MCP_TOKEN", raising=False)
        importlib.reload(_config)
        importlib.reload(_main)


@pytest.fixture()
async def app_with_mcp_enabled_no_token(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[object]:
    """Reload main with ACM_MCP_ENABLED=true and ACM_MCP_TOKEN unset."""
    monkeypatch.setenv("ACM_MCP_ENABLED", "true")
    monkeypatch.delenv("ACM_MCP_TOKEN", raising=False)
    from aerospike_cluster_manager_api import config as _config
    from aerospike_cluster_manager_api import main as _main

    importlib.reload(_config)
    importlib.reload(_main)
    try:
        yield _main.app
    finally:
        monkeypatch.delenv("ACM_MCP_ENABLED", raising=False)
        importlib.reload(_config)
        importlib.reload(_main)


@pytest.fixture()
async def app_with_mcp_disabled_token_set(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[object]:
    """ACM_MCP_ENABLED=false + token set: middleware must NOT be installed
    (the mount itself does not exist)."""
    monkeypatch.delenv("ACM_MCP_ENABLED", raising=False)
    monkeypatch.setenv("ACM_MCP_TOKEN", "should-not-matter")
    from aerospike_cluster_manager_api import config as _config
    from aerospike_cluster_manager_api import main as _main

    importlib.reload(_config)
    importlib.reload(_main)
    try:
        yield _main.app
    finally:
        monkeypatch.delenv("ACM_MCP_TOKEN", raising=False)
        importlib.reload(_config)
        importlib.reload(_main)


async def test_main_mcp_enabled_with_token_gates_mcp_path(
    app_with_mcp_enabled_and_token,
) -> None:
    """End-to-end: ACM_MCP_ENABLED=true + token → /mcp requires bearer."""
    transport = ASGITransport(app=app_with_mcp_enabled_and_token)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # No auth → 401 from MCP middleware.
        resp = await ac.get("/mcp")
        assert resp.status_code == 401
        assert resp.json() == {"detail": "MCP authentication required"}
        # Wrong token → 401.
        resp = await ac.get("/mcp", headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401
        # Correct token → not 401 (the MCP transport itself may still
        # reject a bare GET with 4xx, but it must NOT be the auth 401).
        resp = await ac.get(
            "/mcp",
            headers={"Authorization": "Bearer wired-token"},
        )
        assert resp.status_code != 401, f"correct token must reach MCP transport, got {resp.status_code} {resp.text!r}"


async def test_main_mcp_enabled_with_token_does_not_gate_api(
    app_with_mcp_enabled_and_token,
) -> None:
    """The middleware is installed on the whole app but only enforces on
    ``/mcp/*`` — the rest of the API surface is untouched."""
    transport = ASGITransport(app=app_with_mcp_enabled_and_token)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


async def test_main_mcp_enabled_no_token_passes_through(
    app_with_mcp_enabled_no_token,
) -> None:
    """ACM_MCP_ENABLED=true + ACM_MCP_TOKEN unset: the middleware is
    installed but enforces nothing — /mcp reaches the FastMCP transport
    without an auth 401 from us."""
    transport = ASGITransport(app=app_with_mcp_enabled_no_token)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/mcp")
        # Whatever the transport replies, it must NOT be our 401.
        assert resp.status_code != 401 or resp.json() != {"detail": "MCP authentication required"}


async def test_main_mcp_disabled_with_token_does_not_install_middleware(
    app_with_mcp_disabled_token_set,
) -> None:
    """When the MCP mount itself is off, the middleware must not be
    installed — the path is 404 and even setting a token has no effect."""
    transport = ASGITransport(app=app_with_mcp_disabled_token_set)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/mcp")
        # /mcp is unmounted → 404 from FastAPI's router, NOT 401 from us.
        assert resp.status_code == 404
        # /api routes still work.
        resp = await ac.get("/api/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Smoke: the middleware base class is the right type so ``add_middleware``
# wiring in main.py won't blow up.
# ---------------------------------------------------------------------------


def test_mcp_bearer_token_middleware_is_basehttpmiddleware() -> None:
    from aerospike_cluster_manager_api.mcp.auth import MCPBearerTokenMiddleware

    assert issubclass(MCPBearerTokenMiddleware, BaseHTTPMiddleware)


# Belt-and-braces: the dispatch signature should match Starlette's typing
# contract so pyright doesn't reject the subclass at type-check time.
def test_mcp_bearer_token_middleware_dispatch_signature() -> None:
    import inspect

    from aerospike_cluster_manager_api.mcp.auth import MCPBearerTokenMiddleware

    sig = inspect.signature(MCPBearerTokenMiddleware.dispatch)
    assert list(sig.parameters.keys())[:3] == ["self", "request", "call_next"]


# Static reference to silence "imported but unused" — the imports help
# readers understand that the middleware is exercised against real Starlette
# Request/Response shapes, even when the smoke tests above don't reference
# them directly.
_ = (Request, Response)

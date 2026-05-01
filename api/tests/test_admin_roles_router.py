"""Integration tests for the admin_roles router.

These cover the privilege string→int translation that sits at the router
boundary. aerospike-py's ``Privilege`` TypedDict requires ``code`` to be an
int (PRIV_READ=10, ...), but the REST API and UI surface privileges as
human-readable strings. Without translation, POST /api/admin/{c}/roles 500s
with ``TypeError: 'str' object cannot be interpreted as an integer``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import aerospike_py
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from aerospike_cluster_manager_api.main import app


@asynccontextmanager
async def _noop_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield


@pytest.fixture()
async def client():
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _noop_lifespan

    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.state.limiter.enabled = True
    app.router.lifespan_context = original_lifespan


def _patch_deps(mock_client: AsyncMock):
    """Patch the FastAPI deps so the router resolves to *mock_client*."""
    return (
        patch(
            "aerospike_cluster_manager_api.dependencies.db.get_connection",
            AsyncMock(return_value={"id": "conn-test"}),
        ),
        patch(
            "aerospike_cluster_manager_api.dependencies.client_manager.get_client",
            AsyncMock(return_value=mock_client),
        ),
    )


class TestCreateRole:
    async def test_translates_string_privilege_to_int_code(self, client: AsyncClient):
        """POST with code='read' must call admin_create_role with int code 10."""
        mock_client = AsyncMock()
        mock_client.admin_create_role = AsyncMock(return_value=None)

        deps = _patch_deps(mock_client)
        with deps[0], deps[1]:
            response = await client.post(
                "/api/admin/conn-test/roles",
                json={
                    "name": "analytics_reader",
                    "privileges": [{"code": "read", "namespace": "test", "set": ""}],
                },
            )

        assert response.status_code == 201, response.text
        mock_client.admin_create_role.assert_awaited_once()
        call = mock_client.admin_create_role.await_args
        # Positional: (name, privileges)
        assert call.args[0] == "analytics_reader"
        privileges_arg = call.args[1]
        assert len(privileges_arg) == 1
        assert privileges_arg[0] == {
            "code": aerospike_py.PRIV_READ,  # 10
            "ns": "test",
            "set": "",
        }
        # Sanity: the payload sent to aerospike-py is an int, not a string.
        assert isinstance(privileges_arg[0]["code"], int)

    async def test_translates_each_known_privilege_name(self, client: AsyncClient):
        """All canonical privilege names map to the correct aerospike_py constant."""
        cases = [
            ("read", aerospike_py.PRIV_READ),
            ("read-write", aerospike_py.PRIV_READ_WRITE),
            ("read-write-udf", aerospike_py.PRIV_READ_WRITE_UDF),
            ("write", aerospike_py.PRIV_WRITE),
            ("truncate", aerospike_py.PRIV_TRUNCATE),
            ("user-admin", aerospike_py.PRIV_USER_ADMIN),
            ("sys-admin", aerospike_py.PRIV_SYS_ADMIN),
            ("data-admin", aerospike_py.PRIV_DATA_ADMIN),
            ("udf-admin", aerospike_py.PRIV_UDF_ADMIN),
            ("sindex-admin", aerospike_py.PRIV_SINDEX_ADMIN),
        ]

        for name, expected_int in cases:
            mock_client = AsyncMock()
            mock_client.admin_create_role = AsyncMock(return_value=None)
            deps = _patch_deps(mock_client)
            with deps[0], deps[1]:
                response = await client.post(
                    "/api/admin/conn-test/roles",
                    json={"name": f"role_{name}", "privileges": [{"code": name}]},
                )
            assert response.status_code == 201, f"{name}: {response.text}"
            sent = mock_client.admin_create_role.await_args.args[1][0]
            assert sent["code"] == expected_int, f"{name} -> expected {expected_int}, got {sent['code']}"

    async def test_unknown_privilege_returns_422(self, client: AsyncClient):
        """POST with an unknown privilege string must return 422, not 500."""
        mock_client = AsyncMock()
        mock_client.admin_create_role = AsyncMock(return_value=None)

        deps = _patch_deps(mock_client)
        with deps[0], deps[1]:
            response = await client.post(
                "/api/admin/conn-test/roles",
                json={"name": "bad_role", "privileges": [{"code": "bogus"}]},
            )

        assert response.status_code == 422, response.text
        body = response.json()
        # FastAPI wraps detail in the response body
        detail = body.get("detail", "")
        assert "bogus" in str(detail).lower()
        # admin_create_role must NOT have been called when validation fails
        mock_client.admin_create_role.assert_not_called()

    async def test_namespace_and_set_propagate(self, client: AsyncClient):
        """ns/set scope from the request body must reach aerospike-py unchanged."""
        mock_client = AsyncMock()
        mock_client.admin_create_role = AsyncMock(return_value=None)

        deps = _patch_deps(mock_client)
        with deps[0], deps[1]:
            response = await client.post(
                "/api/admin/conn-test/roles",
                json={
                    "name": "scoped_writer",
                    "privileges": [{"code": "read-write", "namespace": "metrics", "set": "events"}],
                },
            )

        assert response.status_code == 201, response.text
        sent = mock_client.admin_create_role.await_args.args[1][0]
        assert sent == {
            "code": aerospike_py.PRIV_READ_WRITE,
            "ns": "metrics",
            "set": "events",
        }


class TestGetRoles:
    async def test_translates_int_code_back_to_string(self, client: AsyncClient):
        """GET handler must surface privilege codes as canonical strings."""
        mock_client = AsyncMock()
        mock_client.admin_query_roles = AsyncMock(
            return_value=[
                {
                    "role": "analytics_reader",
                    "privileges": [{"code": aerospike_py.PRIV_READ, "ns": "test", "set": ""}],
                    "whitelist": [],
                    "read_quota": 0,
                    "write_quota": 0,
                }
            ]
        )

        deps = _patch_deps(mock_client)
        with deps[0], deps[1]:
            response = await client.get("/api/admin/conn-test/roles")

        assert response.status_code == 200, response.text
        roles = response.json()
        assert len(roles) == 1
        assert roles[0]["name"] == "analytics_reader"
        assert roles[0]["privileges"][0]["code"] == "read"
        assert roles[0]["privileges"][0]["namespace"] == "test"

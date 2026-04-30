"""Unit tests for ``routers._admin_utils.admin_endpoint`` error mapping.

These exercise the decorator directly so we don't need a running Aerospike
cluster or the full FastAPI app stack.
"""

from __future__ import annotations

import pytest
from aerospike_py.exception import AdminError, AerospikeError, ServerError
from fastapi import HTTPException

from aerospike_cluster_manager_api.routers._admin_utils import admin_endpoint


@admin_endpoint
async def _passthrough(*, raise_with: BaseException | None = None) -> str:
    if raise_with is not None:
        raise raise_with
    return "ok"


class TestAdminEndpointDecorator:
    async def test_passes_through_on_success(self) -> None:
        result = await _passthrough()
        assert result == "ok"

    # ----- AdminError → 403 / 404 ------------------------------------------------

    async def test_admin_error_maps_to_403(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(raise_with=AdminError("AEROSPIKE_ERR (52): security not enabled"))
        assert exc_info.value.status_code == 403

    async def test_admin_error_invalid_user_maps_to_404(self) -> None:
        # Rust Debug variant name path
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError("AEROSPIKE_ERR (60): Server error: InvalidUser, In Doubt: false, Node: BB...")
            )
        assert exc_info.value.status_code == 404

    async def test_admin_error_invalid_user_string_fallback(self) -> None:
        # Older aerospike-py versions might surface only the human-readable text.
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(raise_with=AdminError("Invalid user"))
        assert exc_info.value.status_code == 404

    async def test_admin_error_invalid_user_detail_text(self) -> None:
        """404 detail must say 'User not found' specifically when InvalidUser fires."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError("AEROSPIKE_ERR (60): Server error: InvalidUser, In Doubt: false, Node: BB...")
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    async def test_admin_error_invalid_role_detail_text(self) -> None:
        """404 detail must say 'Role not found' specifically when InvalidRole fires."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError("AEROSPIKE_ERR (70): Server error: InvalidRole, In Doubt: false, Node: BB...")
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Role not found"

    # ----- AdminError with NotAuthenticated → 401 (NEW) ------------------------

    async def test_admin_error_not_authenticated_maps_to_401(self) -> None:
        """Code 80 (NotAuthenticated) must surface 401 rather than 403/EE_MSG."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError(
                    "AEROSPIKE_ERR (80): Server error: NotAuthenticated, In Doubt: false, Node: BB..."
                )
            )
        assert exc_info.value.status_code == 401
        # Must NOT bleed the EE_MSG — that would mislead the operator.
        assert "Security is not enabled" not in str(exc_info.value.detail)

    async def test_admin_error_role_violation_maps_to_403_generic(self) -> None:
        """Code 81 (RoleViolation) → 403 with a generic privilege message."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError("AEROSPIKE_ERR (81): Server error: RoleViolation, In Doubt: false, Node: BB...")
            )
        assert exc_info.value.status_code == 403
        assert "Security is not enabled" not in str(exc_info.value.detail)
        assert "privileges" in str(exc_info.value.detail).lower()

    async def test_unknown_admin_error_does_not_leak_ee_msg(self) -> None:
        """Unknown AdminError variants must NOT silently return 403/EE_MSG."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(raise_with=AdminError("AEROSPIKE_ERR (?): Server error: NewUnknownVariant"))
        assert exc_info.value.status_code == 500
        assert "Security is not enabled" not in str(exc_info.value.detail)

    # ----- AdminError dispatch for already-exists (defensive, NEW) -------------

    async def test_admin_error_role_already_exists_maps_to_409(self) -> None:
        """Future aerospike-py may route 71 through AdminError; treat as 409."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError(
                    "AEROSPIKE_ERR (71): Server error: RoleAlreadyExists, In Doubt: false, Node: BB..."
                )
            )
        assert exc_info.value.status_code == 409

    async def test_admin_error_user_already_exists_maps_to_409(self) -> None:
        """Symmetric defensive coverage for code 61 routed through AdminError."""
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=AdminError(
                    "AEROSPIKE_ERR (61): Server error: UserAlreadyExists, In Doubt: false, Node: BB..."
                )
            )
        assert exc_info.value.status_code == 409

    # ----- ServerError → 409 (already exists) -----------------------------------

    async def test_server_error_user_already_exists_maps_to_409(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=ServerError(
                    "AEROSPIKE_ERR (-1): Server error: UserAlreadyExists, In Doubt: false, Node: BB..."
                )
            )
        assert exc_info.value.status_code == 409

    async def test_server_error_role_already_exists_maps_to_409(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=ServerError(
                    "AEROSPIKE_ERR (-1): Server error: RoleAlreadyExists, In Doubt: false, Node: BB..."
                )
            )
        assert exc_info.value.status_code == 409

    async def test_server_error_already_exists_string_fallback(self) -> None:
        # Backward-compat path — older aerospike-py may not embed the variant name.
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(raise_with=ServerError("AEROSPIKE_ERR (61): User already exists"))
        assert exc_info.value.status_code == 409

    # ----- ServerError → 404 (invalid role) -------------------------------------

    async def test_server_error_invalid_role_maps_to_404(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(
                raise_with=ServerError("AEROSPIKE_ERR (-1): Server error: InvalidRole, In Doubt: false, Node: BB...")
            )
        assert exc_info.value.status_code == 404

    # ----- Pass-through for unknown server errors -------------------------------

    async def test_unknown_server_error_propagates(self) -> None:
        original = ServerError("AEROSPIKE_ERR (1): Server error: ServerError, In Doubt: false, Node: BB...")
        with pytest.raises(ServerError):
            await _passthrough(raise_with=original)

    # ----- Generic AerospikeError -----------------------------------------------

    async def test_generic_aerospike_security_text_maps_to_403(self) -> None:
        # Path used as a forward-compat fallback if a future aerospike-py
        # surfaces security errors as plain AerospikeError.
        with pytest.raises(HTTPException) as exc_info:
            await _passthrough(raise_with=AerospikeError("Security not supported on this cluster"))
        assert exc_info.value.status_code == 403

    async def test_generic_aerospike_unrelated_propagates(self) -> None:
        original = AerospikeError("Unrelated transient failure")
        with pytest.raises(AerospikeError):
            await _passthrough(raise_with=original)

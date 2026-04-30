"""Shared utilities for admin (user/role management) routers."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from aerospike_py.exception import AdminError, AerospikeError, ServerError
from fastapi import HTTPException

from aerospike_cluster_manager_api.constants import EE_MSG


def _msg_lower(exc: BaseException) -> str:
    return str(exc).lower()


def _is_security_disabled(msg_lower: str) -> bool:
    """Backward-compat string match used by older aerospike-py releases."""
    return "security" in msg_lower or "not enabled" in msg_lower or "not supported" in msg_lower


def _is_already_exists(exc: BaseException, msg_lower: str) -> bool:
    """Detect "user/role already exists" errors.

    aerospike-py 0.6 maps Aerospike result codes 61 (UserAlreadyExists) and
    71 (RoleAlreadyExists) to plain ``ServerError`` with a message of the form
    ``AEROSPIKE_ERR (-1): Server error: UserAlreadyExists, In Doubt: false,
    Node: ...``. We prefer detecting the Rust ``ResultCode`` Debug variant
    name (which is stable) and fall back to the lowercase human string for
    cross-version compatibility.
    """
    raw = str(exc)
    if "UserAlreadyExists" in raw or "RoleAlreadyExists" in raw:
        return True
    return "already exists" in msg_lower


def _is_invalid_user_or_role(exc: BaseException, msg_lower: str) -> bool:
    """Detect "user/role not found" (Aerospike result codes 60/70).

    Code 60 (``InvalidUser``) is mapped by aerospike-py to ``AdminError``,
    while code 70 (``InvalidRole``) currently falls through to ``ServerError``.
    Both surface as the human string "Invalid user" / "Invalid role" inside
    the message; we prefer the Rust Debug variant name and fall back to the
    string match.
    """
    raw = str(exc)
    if "InvalidUser" in raw or "InvalidRole" in raw:
        return True
    return "invalid user" in msg_lower or "invalid role" in msg_lower


def _user_or_role(exc: BaseException, msg_lower: str) -> str:
    """Disambiguate which side of an "invalid user/role" error fired.

    Returns ``"User"`` or ``"Role"`` so 404 detail messages can surface
    the specific entity. Falls back to ``"User or role"`` when the
    message text is ambiguous.
    """
    raw = str(exc)
    if "InvalidUser" in raw or "invalid user" in msg_lower:
        return "User"
    if "InvalidRole" in raw or "invalid role" in msg_lower:
        return "Role"
    return "User or role"


def _is_not_authenticated(exc: BaseException, msg_lower: str) -> bool:
    """Detect Aerospike result code 80 (``NotAuthenticated``)."""
    raw = str(exc)
    if "NotAuthenticated" in raw:
        return True
    return "not authenticated" in msg_lower


def _is_role_violation(exc: BaseException, msg_lower: str) -> bool:
    """Detect Aerospike result code 81 (``RoleViolation``)."""
    raw = str(exc)
    if "RoleViolation" in raw:
        return True
    return "role violation" in msg_lower


def admin_endpoint(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that maps aerospike-py admin errors to structured HTTP responses.

    Both admin_users and admin_roles routers share this identical error
    handling pattern.  Centralising it here removes duplication and ensures
    consistent behaviour.

    Mapping (preferred via exception class + Rust ``ResultCode`` variant name;
    string match retained as fallback for older aerospike-py builds):

    * ``AdminError`` with InvalidUser → 404 ("User not found")
    * ``AdminError`` with InvalidRole → 404 ("Role not found")
    * ``AdminError`` with UserAlreadyExists / RoleAlreadyExists → 409
      (defensive — future aerospike-py versions may dispatch the
      "already exists" codes through ``AdminError`` instead of the
      generic ``ServerError`` path).
    * ``AdminError`` with NotAuthenticated (code 80) → 401
    * ``AdminError`` with RoleViolation (code 81) → 403 (generic)
    * ``AdminError`` with security/not enabled/not supported text → 403 (EE_MSG)
    * ``AdminError`` with anything else → 500 (do NOT silently surface EE_MSG
      because the message would be misleading for ordinary auth failures).
    * ``ServerError`` with UserAlreadyExists / RoleAlreadyExists → 409
    * ``ServerError`` with InvalidRole → 404
    * other ``AerospikeError`` carrying security text → 403 (legacy)
    * everything else propagates to FastAPI's global handler.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except AdminError as e:
            msg = _msg_lower(e)
            if _is_invalid_user_or_role(e, msg):
                entity = _user_or_role(e, msg)
                raise HTTPException(status_code=404, detail=f"{entity} not found") from None
            if _is_already_exists(e, msg):
                # Defensive: future aerospike-py versions may route 61/71 through
                # AdminError instead of plain ServerError. Treat as 409 here too.
                raise HTTPException(status_code=409, detail="User or role already exists") from None
            if _is_not_authenticated(e, msg):
                raise HTTPException(status_code=401, detail="Authentication required") from None
            if _is_role_violation(e, msg):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient privileges to perform this action",
                ) from None
            if _is_security_disabled(msg):
                raise HTTPException(status_code=403, detail=EE_MSG) from None
            # Unknown AdminError variant — surfacing EE_MSG would mislead the
            # operator (e.g. for 'IllegalState' or 'ExpiredSession'). Promote
            # to 500 so the global handler logs the original exception.
            raise HTTPException(status_code=500, detail="Admin operation failed") from None
        except ServerError as e:
            msg = _msg_lower(e)
            if _is_already_exists(e, msg):
                raise HTTPException(status_code=409, detail="User or role already exists") from None
            if _is_invalid_user_or_role(e, msg):
                entity = _user_or_role(e, msg)
                raise HTTPException(status_code=404, detail=f"{entity} not found") from None
            # Fall through to the global ServerError handler.
            raise
        except AerospikeError as e:
            # Backward-compat fallback: some older aerospike-py builds may surface
            # security errors as a plain AerospikeError without the AdminError
            # subclass. Detect via lowercase string match.
            if _is_security_disabled(_msg_lower(e)):
                raise HTTPException(status_code=403, detail=EE_MSG) from None
            raise

    return wrapper

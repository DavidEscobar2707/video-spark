from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.auth.supabase import AuthenticatedUser, verify_supabase_token
from app.config import get_settings
from app.db.supabase import ensure_user_workspace, get_supabase_client, lookup_user_by_api_key

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name=get_settings().api_key_header, auto_error=False)


def _build_dev_user() -> AuthenticatedUser:
    # TODO: Remove this bypass once Supabase Auth is enforced everywhere.
    return AuthenticatedUser(
        user_id="dev-user",
        tenant_id="dev-user",
        role="owner",
        email="dev@example.com",
        full_name="Dev User",
        auth_type="disabled",
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return ensure_user_workspace(_build_dev_user())

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    return ensure_user_workspace(verify_supabase_token(credentials.credentials))


async def get_current_user_or_api_key(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    api_key: Annotated[str | None, Depends(_api_key_header)],
) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return ensure_user_workspace(_build_dev_user())

    if credentials is not None:
        return ensure_user_workspace(verify_supabase_token(credentials.credentials))

    if api_key:
        user = lookup_user_by_api_key(api_key)
        if user:
            return ensure_user_workspace(user)

    auth_header = request.headers.get("authorization")
    if auth_header:
        _, _, token = auth_header.partition(" ")
        if token:
            return ensure_user_workspace(verify_supabase_token(token))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )


async def get_tenant_id(user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)]) -> str:
    return user.tenant_id


def get_supabase():
    return get_supabase_client()

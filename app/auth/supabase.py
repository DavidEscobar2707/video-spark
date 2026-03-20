from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, get_settings
from app.utils.errors import AuthenticationError


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: str
    tenant_id: str
    role: str = "owner"
    email: str | None = None
    full_name: str | None = None
    auth_type: str = "supabase"
    metadata: dict[str, Any] = Field(default_factory=dict)


def _jwks_url(settings: Settings) -> str:
    if settings.supabase_jwks_url:
        return settings.supabase_jwks_url
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=2)
def _get_jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _build_user_from_payload(payload: dict[str, Any]) -> AuthenticatedUser:
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Supabase token is missing the user id.")

    app_metadata = payload.get("app_metadata") or {}
    user_metadata = payload.get("user_metadata") or {}
    tenant_id = app_metadata.get("tenant_id") or user_id

    return AuthenticatedUser(
        user_id=user_id,
        tenant_id=tenant_id,
        role=app_metadata.get("role") or "owner",
        email=payload.get("email"),
        full_name=user_metadata.get("full_name") or user_metadata.get("name"),
        metadata={
            "app_metadata": app_metadata,
            "user_metadata": user_metadata,
            "session_id": payload.get("session_id"),
        },
    )


def verify_supabase_token(token: str, settings: Settings | None = None) -> AuthenticatedUser:
    settings = settings or get_settings()
    last_error: Exception | None = None

    try:
        signing_key = _get_jwk_client(_jwks_url(settings)).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            options={"verify_aud": False},
        )
        return _build_user_from_payload(payload)
    except Exception as exc:  # pragma: no cover - depends on live token/JWKS behavior
        last_error = exc

    if settings.supabase_jwt_secret:
        try:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return _build_user_from_payload(payload)
        except Exception as exc:  # pragma: no cover - depends on live token/secret behavior
            last_error = exc

    raise AuthenticationError("Invalid Supabase bearer token.") from last_error

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.auth.supabase import AuthenticatedUser
from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def lookup_user_by_api_key(raw_key: str) -> AuthenticatedUser | None:
    hashed = hash_api_key(raw_key)
    response = (
        get_supabase_client()
        .table("users")
        .select("id, tenant_id, role, email, name")
        .eq("api_key", hashed)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None

    record = response.data[0]
    return AuthenticatedUser(
        user_id=record["id"],
        tenant_id=record["tenant_id"],
        role=record.get("role", "member"),
        email=record.get("email"),
        full_name=record.get("name"),
        auth_type="api_key",
    )


_slug_pattern = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _slug_pattern.sub("-", value.lower()).strip("-")
    return slug or "workspace"


def ensure_user_workspace(user: AuthenticatedUser) -> AuthenticatedUser:
    client = get_supabase_client()
    email = user.email or f"{user.user_id}@local.invalid"
    workspace_name = user.full_name or email.split("@")[0] or "Video Workspace"
    workspace_slug = f"{_slugify(workspace_name)}-{user.user_id[:8].lower()}"

    client.table("tenants").upsert(
        {
            "id": user.tenant_id,
            "name": workspace_name,
            "slug": workspace_slug,
        }
    ).execute()
    client.table("users").upsert(
        {
            "id": user.user_id,
            "tenant_id": user.tenant_id,
            "role": user.role,
            "email": email,
            "name": user.full_name or workspace_name,
        }
    ).execute()
    client.table("credits").upsert({"tenant_id": user.tenant_id}).execute()
    return user


@dataclass(slots=True)
class TenantScopedTable:
    table_name: str
    tenant_id: str

    def _table(self) -> Any:
        return get_supabase_client().table(self.table_name)

    def select(self, columns: str = "*") -> Any:
        return self._table().select(columns).eq("tenant_id", self.tenant_id)

    def insert(self, payload: dict[str, Any]) -> Any:
        data = {**payload, "tenant_id": self.tenant_id}
        return self._table().insert(data)

    def update(self, payload: dict[str, Any]) -> Any:
        return self._table().update(payload).eq("tenant_id", self.tenant_id)

    def delete(self) -> Any:
        return self._table().delete().eq("tenant_id", self.tenant_id)


def tenant_table(table_name: str, tenant_id: str) -> TenantScopedTable:
    return TenantScopedTable(table_name=table_name, tenant_id=tenant_id)

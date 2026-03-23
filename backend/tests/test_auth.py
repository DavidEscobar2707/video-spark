from __future__ import annotations

from app.auth.supabase import _build_user_from_payload


def test_supabase_auth_ignores_user_metadata_tenant_override():
    user = _build_user_from_payload(
        {
            "sub": "user-123",
            "email": "user@example.com",
            "app_metadata": {"role": "member"},
            "user_metadata": {"tenant_id": "spoofed-tenant", "full_name": "Example User"},
        }
    )

    assert user.user_id == "user-123"
    assert user.tenant_id == "user-123"
    assert user.role == "member"

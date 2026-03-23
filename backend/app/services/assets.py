from __future__ import annotations

import base64
import binascii
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.auth.supabase import AuthenticatedUser
from app.db.supabase import ensure_user_workspace, get_supabase_client
from app.schemas.asset import AssetOut, AssetUploadRequest
from app.utils.storage import upload_to_storage


def _decode_base64_payload(data_base64: str) -> bytes:
    _, _, encoded = data_base64.partition(",")
    raw_payload = encoded or data_base64
    try:
        return base64.b64decode(raw_payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataBase64 must be a valid base64-encoded image payload.",
        ) from exc


def _asset_storage_path(user: AuthenticatedUser, filename: str, project_id: str | None) -> str:
    suffix = Path(filename).suffix.lower() or ".bin"
    scope = project_id or "library"
    return f"assets/{user.tenant_id}/{scope}/{uuid4()}{suffix}"


def _assert_project_access(tenant_id: str, project_id: str | None) -> None:
    if not project_id:
        return
    response = (
        get_supabase_client()
        .table("projects")
        .select("id")
        .eq("id", project_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")


async def list_assets(tenant_id: str, project_id: str | None = None) -> list[AssetOut]:
    query = (
        get_supabase_client()
        .table("assets")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(100)
    )
    if project_id:
        query = query.eq("project_id", project_id)
    response = query.execute()
    return [AssetOut.model_validate(record) for record in (response.data or [])]


async def upload_asset(user: AuthenticatedUser, payload: AssetUploadRequest) -> AssetOut:
    ensure_user_workspace(user)
    _assert_project_access(user.tenant_id, payload.project_id)

    binary_data = _decode_base64_payload(payload.data_base64)
    storage_path = _asset_storage_path(user, payload.filename, payload.project_id)
    public_url = upload_to_storage(storage_path, binary_data, payload.content_type)
    metadata = {
        "filename": payload.filename,
        "contentType": payload.content_type,
        "sizeBytes": len(binary_data),
        "storagePath": storage_path,
    }

    response = (
        get_supabase_client()
        .table("assets")
        .insert(
            {
                "tenant_id": user.tenant_id,
                "project_id": payload.project_id,
                "type": payload.type,
                "url": public_url,
                "metadata": metadata,
            }
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save asset.")
    return AssetOut.model_validate(response.data[0])

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.supabase import AuthenticatedUser
from app.dependencies import get_current_user_or_api_key
from app.schemas.asset import AssetOut, AssetUploadRequest
from app.services.assets import list_assets, upload_asset

router = APIRouter()


@router.get("/assets", response_model=list[AssetOut])
async def get_assets(
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
    project_id: Annotated[UUID | None, Query(alias="projectId")] = None,
) -> list[AssetOut]:
    resolved_project_id = str(project_id) if project_id else None
    return await list_assets(user.tenant_id, resolved_project_id)


@router.post("/assets/upload", response_model=AssetOut)
async def create_asset(
    payload: AssetUploadRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> AssetOut:
    return await upload_asset(user, payload)

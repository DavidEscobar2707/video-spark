from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.supabase import AuthenticatedUser
from app.dependencies import get_current_user_or_api_key
from app.schemas.project import ProjectOut, StatusResponse
from app.services.projects import get_status, list_projects

router = APIRouter()


@router.get("/projects", response_model=list[ProjectOut])
async def get_projects(
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> list[ProjectOut]:
    return await list_projects(user.tenant_id)


@router.get("/status", response_model=StatusResponse)
async def project_status(
    pid: Annotated[UUID, Query()],
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> StatusResponse:
    return await get_status(user.tenant_id, str(pid))

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.supabase import AuthenticatedUser
from app.dependencies import get_current_user_or_api_key
from app.schemas.project import ProjectDetailResponse, ProjectOut, StatusResponse
from app.schemas.render import RenderRequest, RenderSuccessResponse
from app.services.projects import get_project_detail, get_status, list_projects, rerender_project

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


@router.get("/projects/{pid}", response_model=ProjectDetailResponse)
async def get_project(
    pid: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> ProjectDetailResponse:
    return await get_project_detail(user.tenant_id, str(pid))


@router.post("/projects/{pid}/rerender", response_model=RenderSuccessResponse)
async def rerender_existing_project(
    pid: UUID,
    payload: RenderRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> RenderSuccessResponse:
    result = await rerender_project(user, str(pid), payload)
    return RenderSuccessResponse(
        pid=result["project_id"],
        workflow=result["workflow"],
        webhookUrl=result["webhook_url"],
    )

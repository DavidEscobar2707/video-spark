from __future__ import annotations

from app.db.supabase import get_supabase_client
from app.services.job_queue import get_job_status
from app.schemas.project import ProjectOut, StatusResponse


async def list_projects(tenant_id: str) -> list[ProjectOut]:
    response = (
        get_supabase_client()
        .table("projects")
        .select("id, title, status, workflow, output_video_url, thumbnail_url, duration_seconds, created_at, updated_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [ProjectOut.model_validate(project) for project in (response.data or [])]


async def get_status(tenant_id: str, pid: str) -> StatusResponse:
    return await get_job_status(tenant_id, pid)

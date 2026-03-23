from __future__ import annotations

from fastapi import HTTPException, status

from app.auth.supabase import AuthenticatedUser
from app.db.supabase import get_supabase_client
from app.schemas.project import ProjectDetailResponse, ProjectOut, ProjectVersionOut, StatusResponse
from app.schemas.render import RenderRequest
from app.services.credits import calculate_credits
from app.services.job_queue import create_project_version_job, get_job_status
from app.services.launch import apply_rerender_defaults


def _build_project_version(job: dict) -> ProjectVersionOut:
    pipeline_state = job.get("pipeline_state") or {}
    metadata = {
        "stageLabel": pipeline_state.get("stage", "queued"),
        "workerId": job.get("worker_id"),
        "clipCount": len(job.get("media_urls") or []),
        "downloadReady": bool(job.get("output_video_url")),
    }
    return ProjectVersionOut(
        id=str(job["id"]),
        status=job.get("status", "queued"),
        progress=int(job.get("progress") or 0),
        error_message=job.get("error_message"),
        script_text=job.get("script_text"),
        scenes=job.get("scenes"),
        output_video_url=job.get("output_video_url"),
        worker_id=job.get("worker_id"),
        created_at=job.get("created_at"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        metadata=metadata,
    )


def _get_project_record(tenant_id: str, pid: str) -> dict:
    response = (
        get_supabase_client()
        .table("projects")
        .select("*")
        .eq("id", pid)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return response.data[0]


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


async def get_project_detail(tenant_id: str, pid: str) -> ProjectDetailResponse:
    project = _get_project_record(tenant_id, pid)
    jobs_response = (
        get_supabase_client()
        .table("jobs")
        .select("*")
        .eq("project_id", pid)
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    versions = [_build_project_version(job) for job in (jobs_response.data or [])]
    latest_job = versions[0] if versions else None

    return ProjectDetailResponse(
        **ProjectOut.model_validate(project).model_dump(),
        config=project.get("config") or {},
        latest_job=latest_job,
        versions=versions,
    )


async def rerender_project(
    user: AuthenticatedUser,
    pid: str,
    payload: RenderRequest,
) -> dict[str, str | None]:
    _get_project_record(user.tenant_id, pid)
    normalized_payload = apply_rerender_defaults(payload)
    credits = calculate_credits(normalized_payload)
    job = await create_project_version_job(user, pid, normalized_payload, credits)
    return {
        "project_id": job["project_id"],
        "workflow": normalized_payload.workflow.value,
        "webhook_url": normalized_payload.webhook_url,
    }

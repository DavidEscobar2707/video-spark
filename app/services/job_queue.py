from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.auth.supabase import AuthenticatedUser
from app.config import get_settings
from app.db.supabase import ensure_user_workspace, get_supabase_client
from app.schemas.project import StatusResponse
from app.schemas.render import RenderRequest


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utcnow()).isoformat()


def _project_title(payload: RenderRequest) -> str:
    source_text = payload.source.text or payload.source.prompt or payload.source.url or "Untitled video"
    title = source_text.strip().splitlines()[0][:80]
    return title or "Untitled video"


def _initial_pipeline_state(payload: RenderRequest) -> dict[str, Any]:
    return {
        "stage": "queued",
        "provider": get_settings().video_provider,
        "workflow": payload.workflow.value,
        "sceneOperations": [],
        "ffmpeg": {"stage": "pending"},
    }


def _normalize_job_record(record: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = dict(record)
    normalized["job_id"] = str(record["id"])
    normalized["project_id"] = str(record["project_id"])
    normalized["tenant_id"] = str(record["tenant_id"])
    if config is not None:
        normalized["config"] = config
    return normalized


def _update_project(
    project_id: str,
    tenant_id: str,
    *,
    status_value: str | None = None,
    output_video_url: str | None = None,
) -> None:
    payload: dict[str, Any] = {"updated_at": _iso()}
    if status_value is not None:
        payload["status"] = status_value
    if output_video_url is not None:
        payload["output_video_url"] = output_video_url

    get_supabase_client().table("projects").update(payload).eq("id", project_id).eq(
        "tenant_id", tenant_id
    ).execute()


async def create_render_job(
    user: AuthenticatedUser,
    payload: RenderRequest,
    credits: int,
) -> dict[str, Any]:
    ensure_user_workspace(user)

    client = get_supabase_client()
    now = _iso()
    project_id = str(uuid4())
    job_id = str(uuid4())
    project_config = payload.model_dump(mode="json", by_alias=True, exclude_none=True)

    client.table("projects").upsert(
        {
            "id": project_id,
            "tenant_id": user.tenant_id,
            "user_id": user.user_id,
            "title": _project_title(payload),
            "status": "queued",
            "workflow": payload.workflow.value,
            "config": project_config,
            "updated_at": now,
        }
    ).execute()
    client.table("jobs").insert(
        {
            "id": job_id,
            "project_id": project_id,
            "tenant_id": user.tenant_id,
            "status": "queued",
            "progress": 0,
            "credits_charged": credits,
            "pipeline_state": _initial_pipeline_state(payload),
        }
    ).execute()

    return {
        "project_id": project_id,
        "job_id": job_id,
        "tenant_id": user.tenant_id,
        "workflow": payload.workflow.value,
        "credits": credits,
        "created_at": now,
        "config": project_config,
        "pipeline_state": _initial_pipeline_state(payload),
    }


async def claim_next_job() -> dict[str, Any] | None:
    client = get_supabase_client()
    settings = get_settings()
    stale_before = _iso(_utcnow() - timedelta(seconds=settings.job_lease_seconds))

    response = (
        client.table("jobs")
        .select("*")
        .eq("status", "queued")
        .order("created_at")
        .limit(1)
        .execute()
    )
    candidate = response.data[0] if response.data else None

    if candidate is None:
        stale_response = (
            client.table("jobs")
            .select("*")
            .eq("status", "processing")
            .lt("locked_at", stale_before)
            .order("locked_at")
            .limit(1)
            .execute()
        )
        candidate = stale_response.data[0] if stale_response.data else None

    if candidate is None:
        return None

    project_response = (
        client.table("projects")
        .select("config")
        .eq("id", candidate["project_id"])
        .eq("tenant_id", candidate["tenant_id"])
        .limit(1)
        .execute()
    )
    if not project_response.data:
        await mark_job_failed(
            _normalize_job_record(candidate),
            "Project config is missing for the queued job.",
        )
        return None

    updated_state = {**(candidate.get("pipeline_state") or {}), "stage": "claimed"}
    updated_job = {
        "status": "processing",
        "worker_id": settings.worker_id,
        "locked_at": _iso(),
        "attempt_count": int(candidate.get("attempt_count") or 0) + 1,
        "progress": max(int(candidate.get("progress") or 0), 5),
        "pipeline_state": updated_state,
    }
    if not candidate.get("started_at"):
        updated_job["started_at"] = _iso()

    claim_query = client.table("jobs").update(updated_job).eq("id", candidate["id"]).eq(
        "status", candidate["status"]
    )
    if candidate["status"] == "processing" and candidate.get("locked_at") is not None:
        claim_query = claim_query.eq("locked_at", candidate["locked_at"])
    claim_response = claim_query.execute()
    if not claim_response.data:
        return None

    claimed_candidate = claim_response.data[0]
    _update_project(str(candidate["project_id"]), str(candidate["tenant_id"]), status_value="processing")
    return _normalize_job_record({**candidate, **claimed_candidate}, project_response.data[0]["config"])


async def update_job_state(
    job: dict[str, Any],
    *,
    stage: str | None = None,
    progress: int | None = None,
    status_value: str | None = None,
    project_status: str | None = None,
    error_message: str | None = None,
    output_video_url: str | None = None,
    script_text: str | None = None,
    scenes: list[dict[str, Any]] | None = None,
    voice_url: str | None = None,
    media_urls: list[str] | None = None,
    pipeline_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"locked_at": _iso()}
    state = {**(job.get("pipeline_state") or {})}

    if stage is not None:
        state["stage"] = stage
    if pipeline_extra:
        state.update(pipeline_extra)
    if stage is not None or pipeline_extra:
        payload["pipeline_state"] = state

    if progress is not None:
        payload["progress"] = progress
    if status_value is not None:
        payload["status"] = status_value
    if error_message is not None:
        payload["error_message"] = error_message
    if output_video_url is not None:
        payload["output_video_url"] = output_video_url
    if script_text is not None:
        payload["script_text"] = script_text
    if scenes is not None:
        payload["scenes"] = scenes
    if voice_url is not None:
        payload["voice_url"] = voice_url
    if media_urls is not None:
        payload["media_urls"] = media_urls
    if status_value in {"completed", "failed"}:
        payload["completed_at"] = _iso()

    get_supabase_client().table("jobs").update(payload).eq("id", job["job_id"]).execute()

    if project_status is not None or output_video_url is not None:
        _update_project(
            job["project_id"],
            job["tenant_id"],
            status_value=project_status,
            output_video_url=output_video_url,
        )

    return {**job, **payload, "pipeline_state": state}


async def mark_job_failed(job: dict[str, Any], error_message: str) -> dict[str, Any]:
    return await update_job_state(
        job,
        stage="failed",
        progress=max(int(job.get("progress") or 0), 100),
        status_value="failed",
        project_status="failed",
        error_message=error_message,
    )


async def mark_job_completed(
    job: dict[str, Any],
    output_url: str | None,
    *,
    pipeline_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await update_job_state(
        job,
        stage="completed",
        progress=100,
        status_value="completed",
        project_status="completed",
        output_video_url=output_url,
        pipeline_extra=pipeline_extra,
    )


async def get_job_status(tenant_id: str, pid: str) -> StatusResponse:
    client = get_supabase_client()
    project_response = (
        client.table("projects").select("*").eq("id", pid).eq("tenant_id", tenant_id).limit(1).execute()
    )
    if not project_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    project = project_response.data[0]
    job_response = (
        client.table("jobs")
        .select("*")
        .eq("project_id", pid)
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    job = job_response.data[0] if job_response.data else {}
    pipeline_state = job.get("pipeline_state") or {}

    return StatusResponse(
        pid=str(project["id"]),
        project_status=project.get("status", "queued"),
        job_status=job.get("status", "queued"),
        progress=int(job.get("progress") or 0),
        error_message=job.get("error_message"),
        output_video_url=job.get("output_video_url") or project.get("output_video_url"),
        metadata={
            "tenantId": tenant_id,
            "stageLabel": pipeline_state.get("stage", "queued"),
            "workerId": job.get("worker_id"),
            "clipCount": len(job.get("media_urls") or []),
            "downloadReady": bool(job.get("output_video_url") or project.get("output_video_url")),
        },
    )

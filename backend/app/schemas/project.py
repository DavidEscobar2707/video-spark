from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    status: str
    workflow: str
    output_video_url: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: float | None = None
    created_at: str | None = None
    updated_at: str | None = None


class StatusResponse(BaseModel):
    pid: str
    project_status: str
    job_status: str
    progress: int
    error_message: str | None = None
    output_video_url: str | None = None
    metadata: dict[str, Any] | None = None


class ProjectVersionOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    status: str
    progress: int
    error_message: str | None = None
    script_text: str | None = None
    scenes: list[dict[str, Any]] | None = None
    output_video_url: str | None = None
    worker_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    metadata: dict[str, Any] | None = None


class ProjectDetailResponse(ProjectOut):
    config: dict[str, Any]
    latest_job: ProjectVersionOut | None = None
    versions: list[ProjectVersionOut] = Field(default_factory=list)

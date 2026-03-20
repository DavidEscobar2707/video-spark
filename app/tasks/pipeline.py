from __future__ import annotations

from pathlib import Path

from app.schemas.render import RenderRequest, Workflow
from app.services.job_queue import (
    claim_next_job,
    mark_job_completed,
    mark_job_failed,
    update_job_state,
)
from app.tasks.steps.captions import build_captions
from app.tasks.steps.compose import compose_video
from app.tasks.steps.media import generate_scene_clips
from app.tasks.steps.script import generate_script, split_avatar_scenes, split_scenes
from app.tasks.steps.voice import generate_voice
from app.config import get_settings
from app.utils.storage import upload_file_to_storage


def upload_final_video(local_path: str, runtime_config: dict[str, object]) -> str:
    settings = get_settings()
    final_path = Path(local_path)
    storage_path = "/".join(
        [
            "renders",
            str(runtime_config["tenantId"]),
            str(runtime_config["projectId"]),
            str(runtime_config["jobId"]),
            final_path.name,
        ]
    )
    return upload_file_to_storage(
        final_path,
        storage_path,
        bucket=settings.supabase_videos_bucket,
        content_type="video/mp4",
    )


async def _run_pipeline(job: dict[str, object]) -> dict[str, object]:
    payload = RenderRequest.model_validate(job["config"])
    runtime_config = {
        "jobId": job["job_id"],
        "projectId": job["project_id"],
        "tenantId": job["tenant_id"],
        "workflow": payload.workflow.value,
        "resolution": payload.render.resolution.value if payload.render.resolution else "720p",
        "aspectRatio": str(payload.aspect_ratio or "9:16"),
    }

    if payload.workflow == Workflow.AVATAR_TO_VIDEO:
        return await _run_avatar_pipeline(job, payload, runtime_config)

    job = await update_job_state(job, stage="generating_script", progress=15)
    script = await generate_script(payload)
    scenes = await split_scenes(script, payload)
    job = await update_job_state(
        job,
        stage="script_ready",
        progress=30,
        script_text=script,
        scenes=scenes,
    )

    job = await update_job_state(job, stage="generating_voice", progress=45)
    voice_artifact = await generate_voice(
        script,
        payload.voice.model_dump(mode="json", by_alias=True),
        runtime_config,
    )
    voice_path = voice_artifact["audioPath"] if voice_artifact else None
    job = await update_job_state(
        job,
        stage="voice_ready",
        progress=55,
        voice_url=voice_path,
        pipeline_extra={"voiceLocalPath": voice_path, "voiceModel": voice_artifact["modelId"] if voice_artifact else None},
    )

    job = await update_job_state(job, stage="building_captions", progress=62)
    caption_artifacts = await build_captions(
        voice_artifact,
        payload.captions.model_dump(mode="json", by_alias=True),
        runtime_config,
    )
    job = await update_job_state(
        job,
        stage="captions_ready",
        progress=68,
        pipeline_extra={
            "subtitleAssPath": caption_artifacts["assPath"] if caption_artifacts else None,
            "subtitleSrtPath": caption_artifacts["srtPath"] if caption_artifacts else None,
        },
    )

    job = await update_job_state(job, stage="generating_clips", progress=70)
    media_urls: list[str] = []
    scene_operations: list[dict[str, object]] = []
    total_scenes = max(len(scenes), 1)
    async for clip in generate_scene_clips(scenes, runtime_config):
        media_urls.append(str(clip["clipPath"]))
        scene_operations.append(
            {
                "sceneIndex": clip["sceneIndex"],
                "operationName": clip["operationName"],
                "prompt": clip["prompt"],
                "clipPath": clip["clipPath"],
                "durationSeconds": clip["durationSeconds"],
                "status": "ready",
            }
        )
        progress = 70 + int((len(media_urls) / total_scenes) * 15)
        job = await update_job_state(
            job,
            stage="generating_clips",
            progress=min(progress, 84),
            pipeline_extra={"sceneOperations": scene_operations},
        )
    job = await update_job_state(
        job,
        stage="clips_ready",
        progress=85,
        media_urls=media_urls,
        pipeline_extra={"sceneOperations": scene_operations},
    )

    job = await update_job_state(job, stage="assembling_video", progress=92)
    final_path = await compose_video(
        scenes,
        media_urls,
        voice_path,
        caption_artifacts["assPath"] if caption_artifacts else None,
        runtime_config,
    )
    job = await update_job_state(job, stage="uploading_output", progress=97)
    output_url = upload_final_video(final_path, runtime_config)
    return await mark_job_completed(
        job,
        output_url,
        pipeline_extra={"finalLocalPath": final_path},
    )


async def _run_avatar_pipeline(
    job: dict[str, object],
    payload: RenderRequest,
    runtime_config: dict[str, object],
) -> dict[str, object]:
    runtime_config = {**runtime_config, "preserveClipAudio": True}

    job = await update_job_state(job, stage="planning_avatar_video", progress=15)
    script = await generate_script(payload)
    scenes = await split_avatar_scenes(script, payload)
    job = await update_job_state(
        job,
        stage="avatar_plan_ready",
        progress=28,
        script_text=script,
        scenes=scenes,
        pipeline_extra={"avatarPreset": payload.avatar.preset_id if payload.avatar else "default-avatar"},
    )

    media_urls: list[str] = []
    scene_operations: list[dict[str, object]] = []
    total_scenes = max(len(scenes), 1)

    async for clip in generate_scene_clips(scenes, runtime_config):
        media_urls.append(str(clip["clipPath"]))
        scene_operations.append(
            {
                "sceneIndex": clip["sceneIndex"],
                "operationName": clip["operationName"],
                "prompt": clip["prompt"],
                "clipPath": clip["clipPath"],
                "durationSeconds": clip["durationSeconds"],
                "status": "ready",
            }
        )
        current_stage = "generating_avatar_scene" if int(clip["sceneIndex"]) == 0 else "generating_broll_scenes"
        progress = 35 + int((len(media_urls) / total_scenes) * 45)
        job = await update_job_state(
            job,
            stage=current_stage,
            progress=min(progress, 82),
            pipeline_extra={"sceneOperations": scene_operations},
        )

    job = await update_job_state(
        job,
        stage="clips_ready",
        progress=85,
        media_urls=media_urls,
        pipeline_extra={"sceneOperations": scene_operations},
    )

    job = await update_job_state(job, stage="assembling_video", progress=92)
    final_path = await compose_video(
        scenes,
        media_urls,
        None,
        None,
        runtime_config,
    )
    job = await update_job_state(job, stage="uploading_output", progress=97)
    output_url = upload_final_video(final_path, runtime_config)
    return await mark_job_completed(
        job,
        output_url,
        pipeline_extra={"finalLocalPath": final_path},
    )


async def process_next_job() -> bool:
    job = await claim_next_job()
    if job is None:
        return False

    try:
        await _run_pipeline(job)
    except Exception as exc:  # pragma: no cover - placeholder until queue persistence is real
        await mark_job_failed(job, str(exc))
    return True

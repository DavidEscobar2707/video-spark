from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from app.config import get_settings
from app.services.ffmpeg_svc import image_segment_command, run_media_command
from app.services.image_provider import get_image_provider


async def generate_story_segments(
    scenes: list[dict[str, object]],
    config: dict[str, object],
) -> AsyncIterator[dict[str, object]]:
    provider = get_image_provider()
    settings = get_settings()
    job_id = str(config.get("jobId") or "job")
    segments_dir = Path(settings.worker_artifacts_dir) / job_id / "story-segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    for index, scene in enumerate(scenes):
        artifact = await provider.generate_story_image(
            str(scene.get("visualPrompt") or scene.get("text") or "Story frame"),
            {**config, "imageIndex": index},
        )
        segment_path = segments_dir / f"segment-{index:02d}.mp4"
        await run_media_command(
            image_segment_command(
                Path(artifact.image_path),
                segment_path,
                duration_seconds=float(scene.get("durationSeconds") or 5),
            )
        )
        yield {
            "sceneIndex": index,
            "clipPath": segment_path.as_posix(),
            "imagePath": artifact.image_path,
            "operationName": artifact.provider_ref or f"image-{index}",
            "prompt": artifact.prompt,
            "durationSeconds": scene.get("durationSeconds"),
        }

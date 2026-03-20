from __future__ import annotations

from collections.abc import AsyncIterator

from app.services.video_provider import get_video_provider


async def generate_scene_clips(
    scenes: list[dict[str, object]],
    config: dict[str, object],
) -> AsyncIterator[dict[str, object]]:
    """Generate Veo clips one scene at a time and yield local artifact metadata."""

    provider = get_video_provider()

    for index, scene in enumerate(scenes):
        operation = await provider.start_scene_clip(scene, {**config, "sceneIndex": index})
        result = await provider.poll_scene_clip(operation, {**config, "sceneIndex": index})
        if result.clip_path is None:
            continue
        yield {
            "sceneIndex": index,
            "clipPath": result.clip_path,
            "operationName": result.metadata.get("operationName") if result.metadata else operation.external_ref,
            "prompt": result.metadata.get("prompt") if result.metadata else operation.prompt,
            "durationSeconds": scene.get("durationSeconds"),
        }

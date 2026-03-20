from __future__ import annotations

import asyncio
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

from google import genai
from google.genai import types

from app.config import Settings, get_settings
from app.utils.errors import ExternalServiceError
from app.utils.http import get_async_client


@dataclass(slots=True)
class ProviderOperation:
    request_id: str
    status: str
    external_ref: str
    prompt: str
    scene_index: int
    raw_operation: Any | None = None


@dataclass(slots=True)
class ProviderResult:
    status: str
    clip_path: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class VideoProvider(Protocol):
    async def start_scene_clip(self, scene: dict[str, object], config: dict[str, object]) -> ProviderOperation:
        ...

    async def poll_scene_clip(self, operation: ProviderOperation, config: dict[str, object]) -> ProviderResult:
        ...


def _build_genai_client(settings: Settings) -> genai.Client:
    if not settings.gemini_api_key or settings.gemini_api_key == "your-gemini-api-key":
        raise ExternalServiceError("GEMINI_API_KEY is required to generate real Veo clips.")
    return genai.Client(api_key=settings.gemini_api_key)


def _normalize_duration_seconds(requested: int, resolution: str) -> int:
    if resolution in {"1080p", "4k"}:
        return 8
    if requested <= 5:
        return 4
    if requested <= 7:
        return 6
    return 8


def _build_scene_prompt(scene: dict[str, object]) -> str:
    visual_prompt = str(scene.get("visualPrompt") or scene.get("text") or "").strip()
    if not visual_prompt:
        visual_prompt = "Create a short cinematic vertical social video scene."

    spoken_text = str(scene.get("spokenText") or "").strip()
    shot_type = str(scene.get("shotType") or "").strip()
    prompt_parts = [visual_prompt]

    if spoken_text and scene.get("generateAudio"):
        if shot_type == "talking-head":
            prompt_parts.append(
                f'The presenter says exactly: "{spoken_text}". Keep facial performance natural and lip movement synchronized to the dialogue.'
            )
        else:
            prompt_parts.append(
                f'The narration in this shot says exactly: "{spoken_text}". The same presenter remains visually consistent with the avatar reference.'
            )

    prompt_parts.append("Vertical 9:16 framing. No subtitles or text overlay.")
    return " ".join(part for part in prompt_parts if part).strip()


def _job_dir(settings: Settings, job_id: str) -> Path:
    return Path(settings.worker_artifacts_dir) / job_id


async def _reference_image(scene: dict[str, object]) -> types.VideoGenerationReferenceImage | None:
    reference_url = str(scene.get("referenceImageUrl") or "").strip()
    if not reference_url:
        return None

    parsed = urlparse(reference_url)
    mime_type = str(scene.get("referenceImageMimeType") or "").strip() or None
    if parsed.scheme in {"http", "https"}:
        response = await get_async_client().get(reference_url)
        response.raise_for_status()
        image_bytes = response.content
        mime_type = mime_type or response.headers.get("content-type", "").split(";")[0].strip() or "image/png"
    else:
        source_path = Path(reference_url)
        image_bytes = source_path.read_bytes()
        mime_type = mime_type or mimetypes.guess_type(source_path.name)[0] or "image/png"

    reference_type = types.VideoGenerationReferenceType(
        str(scene.get("referenceType") or "ASSET").upper()
    )
    return types.VideoGenerationReferenceImage(
        image=types.Image(image_bytes=image_bytes, mime_type=mime_type),
        reference_type=reference_type,
    )


class GeminiVeoVideoProvider:
    def __init__(
        self,
        *,
        client_factory: Any | None = None,
        settings_factory: Any | None = None,
    ) -> None:
        self._settings_factory = settings_factory or get_settings
        self._client_factory = client_factory
        self._client: genai.Client | Any | None = None

    def _settings(self) -> Settings:
        return self._settings_factory()

    def _client_instance(self) -> genai.Client | Any:
        if self._client is None:
            settings = self._settings()
            factory = self._client_factory or _build_genai_client
            self._client = factory(settings)
        return self._client

    def _clip_output_path(self, config: dict[str, object], scene_index: int) -> Path:
        settings = self._settings()
        job_id = str(config.get("jobId") or "job")
        clip_dir = _job_dir(settings, job_id) / "clips"
        clip_dir.mkdir(parents=True, exist_ok=True)
        return clip_dir / f"scene-{scene_index:02d}.mp4"

    async def _generate_video_operation(
        self,
        *,
        client: genai.Client | Any,
        settings: Settings,
        prompt: str,
        config: types.GenerateVideosConfig,
    ) -> Any:
        try:
            return await asyncio.to_thread(
                client.models.generate_videos,
                model=settings.video_provider_model,
                prompt=prompt,
                config=config,
            )
        except Exception as exc:
            if config.generate_audio and "generate_audio parameter is not supported in Gemini API" in str(exc):
                fallback_config = types.GenerateVideosConfig.model_validate(
                    {
                        key: value
                        for key, value in config.model_dump(exclude_none=True).items()
                        if key != "generate_audio"
                    }
                )
                return await asyncio.to_thread(
                    client.models.generate_videos,
                    model=settings.video_provider_model,
                    prompt=prompt,
                    config=fallback_config,
                )
            raise

    async def start_scene_clip(self, scene: dict[str, object], config: dict[str, object]) -> ProviderOperation:
        settings = self._settings()
        client = self._client_instance()
        scene_index = int(config.get("sceneIndex") or 0)
        resolution = str(config.get("resolution") or "720p")
        duration_seconds = _normalize_duration_seconds(
            int(scene.get("durationSeconds") or 6),
            resolution,
        )
        prompt = _build_scene_prompt(scene)
        reference_image = await _reference_image(scene)
        config_payload: dict[str, object] = {
            "aspect_ratio": str(config.get("aspectRatio") or "9:16"),
            "duration_seconds": duration_seconds,
            "number_of_videos": 1,
            "resolution": resolution,
        }
        if scene.get("generateAudio"):
            config_payload["generate_audio"] = True
        if reference_image is not None:
            config_payload["reference_images"] = [reference_image]

        generation_config = types.GenerateVideosConfig.model_validate(
            config_payload
        )
        raw_operation = await self._generate_video_operation(
            client=client,
            settings=settings,
            prompt=prompt,
            config=generation_config,
        )
        operation_name = str(getattr(raw_operation, "name", "") or uuid4())
        return ProviderOperation(
            request_id=str(uuid4()),
            status="submitted",
            external_ref=operation_name,
            prompt=prompt,
            scene_index=scene_index,
            raw_operation=raw_operation,
        )

    async def poll_scene_clip(self, operation: ProviderOperation, config: dict[str, object]) -> ProviderResult:
        settings = self._settings()
        client = self._client_instance()
        current = operation.raw_operation
        deadline = time.monotonic() + settings.video_generation_timeout_seconds

        if current is None:
            raise ExternalServiceError(
                "The Veo operation handle is missing; restart the job to regenerate the scene."
            )

        while not getattr(current, "done", False):
            if time.monotonic() >= deadline:
                raise ExternalServiceError(
                    f"Timed out waiting for Veo to finish scene {operation.scene_index}."
                )
            await asyncio.sleep(settings.video_poll_interval_seconds)
            current = await asyncio.to_thread(client.operations.get, current)

        if getattr(current, "error", None):
            raise ExternalServiceError(str(current.error))

        response = getattr(current, "response", None)
        generated_videos = getattr(response, "generated_videos", None) if response is not None else None
        if not generated_videos:
            raise ExternalServiceError("Veo returned no generated videos.")

        generated_video = generated_videos[0]
        video_file = getattr(generated_video, "video", None)
        if video_file is None:
            raise ExternalServiceError("Veo returned a generation without a downloadable video file.")

        output_path = self._clip_output_path(config, operation.scene_index)
        await asyncio.to_thread(client.files.download, file=video_file)
        await asyncio.to_thread(video_file.save, output_path.as_posix())

        return ProviderResult(
            status="ready",
            clip_path=output_path.as_posix(),
            metadata={
                "operationName": str(getattr(current, "name", operation.external_ref)),
                "prompt": operation.prompt,
                "sceneIndex": operation.scene_index,
            },
        )


def get_video_provider() -> VideoProvider:
    return GeminiVeoVideoProvider()

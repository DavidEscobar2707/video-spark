from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.utils.errors import ExternalServiceError, PipelineStepError
from app.utils.http import get_async_client, request_with_retry


@dataclass(slots=True)
class ImageArtifact:
    image_path: str
    prompt: str
    provider_ref: str | None = None


class OpenAIImageProvider:
    async def generate_story_image(
        self,
        prompt: str,
        runtime_config: dict[str, object],
    ) -> ImageArtifact:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ExternalServiceError("OPENAI_API_KEY is required for image-story renders.")

        timeout = httpx.Timeout(
            connect=20.0,
            read=float(settings.image_generation_timeout_seconds),
            write=60.0,
            pool=20.0,
        )
        try:
            response = await request_with_retry(
                "POST",
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.image_provider_model,
                    "prompt": prompt,
                    "size": "1024x1536",
                },
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise ExternalServiceError(
                f"Image generation timed out after {settings.image_generation_timeout_seconds} seconds."
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Image generation request failed: {exc!r}") from exc
        if response.status_code >= 400:
            raise ExternalServiceError(f"Image generation failed: {response.text}")

        data = response.json().get("data") or []
        if not data:
            raise ExternalServiceError("Image generation returned no images.")

        job_id = str(runtime_config.get("jobId") or "job")
        image_index = int(runtime_config.get("imageIndex") or 0)
        image_dir = Path(settings.worker_artifacts_dir) / job_id / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / f"story-{image_index:02d}.png"

        if data[0].get("b64_json"):
            image_path.write_bytes(base64.b64decode(data[0]["b64_json"]))
        elif data[0].get("url"):
            try:
                download = await get_async_client().get(str(data[0]["url"]), timeout=timeout)
                download.raise_for_status()
                image_path.write_bytes(download.content)
            except httpx.TimeoutException as exc:
                raise ExternalServiceError(
                    f"Image download timed out after {settings.image_generation_timeout_seconds} seconds."
                ) from exc
            except httpx.HTTPError as exc:
                raise ExternalServiceError(f"Image download failed: {exc!r}") from exc
        else:
            raise ExternalServiceError("Image generation returned neither b64_json nor url.")

        return ImageArtifact(
            image_path=image_path.as_posix(),
            prompt=prompt,
            provider_ref=str(data[0].get("revised_prompt") or data[0].get("url") or ""),
        )


def get_image_provider() -> OpenAIImageProvider:
    settings = get_settings()
    if settings.image_provider != "openai-images":
        raise PipelineStepError(f"Unsupported image provider: {settings.image_provider}")
    return OpenAIImageProvider()

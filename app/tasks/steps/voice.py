from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.utils.errors import ExternalServiceError, PipelineStepError
from app.utils.http import request_with_retry


def _job_dir(job_id: str) -> Path:
    settings = get_settings()
    job_dir = Path(settings.worker_artifacts_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


async def generate_voice(
    script: str,
    voice_config: dict[str, Any],
    runtime_config: dict[str, object],
) -> dict[str, Any] | None:
    """Generate narration audio plus character alignment using ElevenLabs."""

    if not voice_config.get("enabled", True):
        return None

    settings = get_settings()
    if settings.voice_provider != "elevenlabs":
        raise PipelineStepError(f"Unsupported voice provider: {settings.voice_provider}")
    if not settings.elevenlabs_api_key:
        raise ExternalServiceError("ELEVENLABS_API_KEY is required when voice generation is enabled.")

    voice_id = voice_config.get("voiceId") or voice_config.get("voice_id") or settings.default_voice_id
    if not voice_id:
        raise PipelineStepError("No ElevenLabs voice is configured for the current render.")

    payload: dict[str, Any] = {
        "text": script,
        "model_id": settings.elevenlabs_model_id,
        "output_format": settings.elevenlabs_output_format,
    }
    language = voice_config.get("language") or settings.default_voice_language
    if language:
        payload["language_code"] = language

    voice_settings: dict[str, Any] = {}
    if voice_config.get("stability") is not None:
        voice_settings["stability"] = voice_config["stability"]
    if voice_config.get("speed") is not None:
        voice_settings["speed"] = voice_config["speed"]
    if voice_settings:
        payload["voice_settings"] = voice_settings

    url = f"{settings.elevenlabs_api_base_url}/v1/text-to-speech/{voice_id}/with-timestamps"
    response = await request_with_retry(
        "POST",
        url,
        headers={
            "xi-api-key": settings.elevenlabs_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if response.status_code >= 400:
        raise ExternalServiceError(f"ElevenLabs voice generation failed: {response.text}")

    data = response.json()
    audio_base64 = data.get("audio_base64")
    if not audio_base64:
        raise ExternalServiceError("ElevenLabs returned no audio payload.")

    job_dir = _job_dir(str(runtime_config.get("jobId") or "job"))
    audio_dir = job_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / "voice-track.mp3"
    audio_path.write_bytes(base64.b64decode(audio_base64))

    alignment = data.get("normalized_alignment") or data.get("alignment")
    if not alignment:
        raise ExternalServiceError("ElevenLabs returned no alignment data for subtitle generation.")

    return {
        "audioPath": audio_path.as_posix(),
        "alignment": alignment,
        "requestId": response.headers.get("request-id"),
        "voiceId": voice_id,
        "modelId": settings.elevenlabs_model_id,
        "language": language,
    }

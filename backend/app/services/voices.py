from __future__ import annotations

import urllib.parse

from app.config import get_settings
from app.schemas.render import VoiceListResponse, VoiceOption
from app.utils.errors import ExternalServiceError
from app.utils.http import request_with_retry


def _thumbnail_data_url(name: str, labels: dict[str, str]) -> str:
    initials = "".join(part[:1].upper() for part in name.split()[:2]) or "VS"
    subtitle = labels.get("accent") or labels.get("use_case") or "voice"
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#111827"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="36" fill="url(#bg)"/>
  <circle cx="128" cy="92" r="42" fill="#f3f4f6" opacity="0.18"/>
  <text x="128" y="112" text-anchor="middle" font-size="44" font-family="Arial" font-weight="700" fill="#f9fafb">{initials}</text>
  <text x="128" y="184" text-anchor="middle" font-size="18" font-family="Arial" fill="#dbeafe">{subtitle[:20]}</text>
</svg>
""".strip()
    return f"data:image/svg+xml;charset=utf-8,{urllib.parse.quote(svg)}"


def _resolve_language(voice_payload: dict) -> str | None:
    verified_languages = voice_payload.get("verified_languages") or []
    if verified_languages:
        language = verified_languages[0].get("language")
        if language:
            return str(language)
    labels = voice_payload.get("labels") or {}
    if labels.get("language"):
        return str(labels["language"])
    fine_tuning = voice_payload.get("fine_tuning") or {}
    if fine_tuning.get("language"):
        return str(fine_tuning["language"])
    return None


async def list_available_voices() -> VoiceListResponse:
    settings = get_settings()
    if settings.voice_provider != "elevenlabs":
        raise ExternalServiceError("Voice listing only supports the ElevenLabs provider in the MVP.")
    if not settings.elevenlabs_api_key:
        raise ExternalServiceError("ELEVENLABS_API_KEY is required to list voices.")

    response = await request_with_retry(
        "GET",
        f"{settings.elevenlabs_api_base_url}/v1/voices",
        headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "application/json"},
    )
    if response.status_code >= 400:
        raise ExternalServiceError(f"ElevenLabs voice listing failed: {response.text}")

    payload = response.json()
    options: list[VoiceOption] = []
    for voice in payload.get("voices") or []:
        labels = {str(key): str(value) for key, value in (voice.get("labels") or {}).items() if value is not None}
        options.append(
            VoiceOption(
                voiceId=str(voice["voice_id"]),
                name=str(voice.get("name") or "Unnamed Voice"),
                language=_resolve_language(voice),
                labels=labels,
                previewAudioUrl=voice.get("preview_url"),
                thumbnailUrl=_thumbnail_data_url(str(voice.get("name") or "Voice"), labels),
                isDefault=str(voice["voice_id"]) == settings.default_voice_id,
            )
        )

    options.sort(key=lambda item: (not item.is_default, item.name.lower()))
    return VoiceListResponse(voices=options)

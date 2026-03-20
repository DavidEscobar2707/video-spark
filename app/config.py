from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    auth_enabled: bool = True
    api_version: str = "0.1.0"
    app_name: str = "VideoSpark API"
    app_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    log_level: str = "INFO"

    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: str = ""
    supabase_jwks_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_assets_bucket: str = "assets"
    supabase_videos_bucket: str = "videos"

    openai_api_key: str = ""
    gemini_api_key: str = ""
    video_provider: str = "gemini-veo"
    video_provider_model: str = "veo-3.1-generate-preview"
    script_provider: str = "openai"
    voice_provider: str = "elevenlabs"

    elevenlabs_api_key: str = ""
    elevenlabs_api_base_url: str = "https://api.elevenlabs.io"
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"
    default_voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    default_voice_language: str = "en"
    default_avatar_image_url: str = ""
    default_avatar_image_mime_type: str = "image/png"
    default_avatar_name: str = "Studio Host"
    default_avatar_character_prompt: str = (
        "A polished on-camera presenter with confident delivery, clean wardrobe, and premium social-video styling."
    )

    default_free_credits: int = 70
    first_video_bonus_credits: int = 10
    api_key_header: str = "key"
    webhook_timeout_seconds: int = 10
    worker_id: str = "local-worker"
    worker_poll_interval_seconds: int = 5
    job_lease_seconds: int = 120
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    worker_temp_dir: str = "/tmp/videospark-worker"
    worker_artifacts_dir: str = "/tmp/videospark-worker"
    video_poll_interval_seconds: int = 10
    video_generation_timeout_seconds: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            if value.strip().startswith("["):
                return [str(item).strip() for item in json.loads(value)]
            return [item.strip() for item in value.split(",") if item.strip()]
        return ["http://localhost:3000"]

    @property
    def is_local_env(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "test", "local"}


def ensure_runtime_settings(settings: Settings | None = None) -> Settings:
    settings = settings or get_settings()
    if not settings.auth_enabled and not settings.is_local_env:
        raise RuntimeError("AUTH_ENABLED=false is only allowed in local or test environments.")
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

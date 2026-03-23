from __future__ import annotations

from fastapi import HTTPException, status

from app.config import get_settings
from app.services.caption_presets import normalize_caption_preset
from app.schemas.render import (
    AspectRatio,
    AvatarRenderRequest,
    ImageStoryRenderRequest,
    MediaType,
    RenderRequest,
    RenderResolution,
    Workflow,
)

SUPPORTED_WORKFLOWS = {Workflow.SCRIPT_TO_VIDEO, Workflow.PROMPT_TO_VIDEO}
SUPPORTED_MEDIA_TYPES = {MediaType.AI_VIDEO}
SUPPORTED_RESOLUTIONS = {RenderResolution.P720, RenderResolution.P1080, None}
SUPPORTED_CAPTION_PRESETS = {
    None,
    "",
    "karaoke",
    "karaoke-social",
    "karaoke-bold",
    "karaoke-clean",
    "karaoke-pop",
}


def validate_launch_config(config: RenderRequest) -> None:
    errors: list[str] = []

    if config.workflow not in SUPPORTED_WORKFLOWS:
        errors.append("Only prompt-to-video and script-to-video are supported in launch mode.")

    if config.media.type not in SUPPORTED_MEDIA_TYPES:
        errors.append("Only ai-video is supported in launch mode.")

    if config.project_id:
        errors.append("projectId is server-managed in launch mode.")

    if config.captions.enabled and not config.voice.enabled:
        errors.append("Interactive captions require voice.enabled=true in launch mode.")

    if config.captions.preset not in SUPPORTED_CAPTION_PRESETS:
        errors.append("Only the supported karaoke caption presets are available in launch mode.")

    if config.music.enabled:
        errors.append("Music is recognized but not supported in launch mode.")

    if config.source.url:
        errors.append("Article URL ingestion is deferred until after the launch video pipeline.")

    if config.aspect_ratio not in {None, AspectRatio.NINE_SIXTEEN, "9:16"}:
        errors.append("Only 9:16 output is supported in launch mode.")

    if config.render.resolution not in SUPPORTED_RESOLUTIONS:
        errors.append("Only 720p and 1080p are supported in launch mode.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=errors,
        )


def apply_launch_defaults(config: RenderRequest) -> RenderRequest:
    settings = get_settings()

    if config.voice.enabled and not config.voice.voice_id:
        config.voice.voice_id = settings.default_voice_id
    if config.voice.enabled and not config.voice.language:
        config.voice.language = settings.default_voice_language
    if config.captions.enabled and not config.captions.preset:
        config.captions.preset = "karaoke-clean"
    elif config.captions.enabled:
        config.captions.preset = normalize_caption_preset(config.captions.preset)

    return config


def validate_avatar_render_config(config: AvatarRenderRequest) -> None:
    errors: list[str] = []
    settings = get_settings()

    if not settings.default_avatar_image_url:
        errors.append("DEFAULT_AVATAR_IMAGE_URL must be configured before avatar-render can be used.")

    if config.music.enabled:
        errors.append("Music is not supported for avatar-render.")

    if config.captions.enabled:
        errors.append("Captions are not supported for avatar-render yet.")

    if config.aspect_ratio not in {None, AspectRatio.NINE_SIXTEEN, "9:16"}:
        errors.append("Only 9:16 output is supported for avatar-render.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=errors,
        )


def apply_avatar_render_defaults(config: AvatarRenderRequest) -> RenderRequest:
    settings = get_settings()

    return RenderRequest.model_validate(
        {
            "workflow": Workflow.AVATAR_TO_VIDEO.value,
            "webhookUrl": config.webhook_url,
            "source": config.source.model_dump(mode="json", by_alias=True, exclude_none=True),
            "media": {
                "type": MediaType.AI_VIDEO.value,
                "quality": "standard",
            },
            "voice": {"enabled": False},
            "captions": {"enabled": False},
            "music": config.music.model_dump(mode="json", by_alias=True, exclude_none=True),
            "options": config.options.model_dump(mode="json", by_alias=True, exclude_none=True),
            "render": {
                **config.render.model_dump(mode="json", by_alias=True, exclude_none=True),
                "resolution": RenderResolution.P720.value,
            },
            "avatar": {
                "enabled": True,
                "presetId": "default-avatar",
                "url": settings.default_avatar_image_url,
                "mimeType": settings.default_avatar_image_mime_type,
            },
            "metadata": config.metadata,
            "aspectRatio": AspectRatio.NINE_SIXTEEN.value,
        }
    )


def validate_image_story_render_config(config: ImageStoryRenderRequest) -> None:
    errors: list[str] = []

    if config.aspect_ratio not in {None, AspectRatio.NINE_SIXTEEN, "9:16"}:
        errors.append("Only 9:16 output is supported for image-story-render.")

    if config.captions.enabled and not config.voice.enabled:
        errors.append("Interactive captions require voice.enabled=true for image-story-render.")

    if config.captions.preset not in SUPPORTED_CAPTION_PRESETS:
        errors.append("Unsupported caption preset for image-story-render.")

    if config.render.resolution not in SUPPORTED_RESOLUTIONS:
        errors.append("Only 720p and 1080p are supported for image-story-render.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=errors,
        )


def apply_image_story_defaults(config: ImageStoryRenderRequest) -> RenderRequest:
    settings = get_settings()

    voice_payload = config.voice.model_dump(mode="json", by_alias=True, exclude_none=True)
    if voice_payload.get("enabled", True) and not voice_payload.get("voiceId"):
        voice_payload["voiceId"] = settings.default_voice_id
    if voice_payload.get("enabled", True) and not voice_payload.get("language"):
        voice_payload["language"] = settings.default_voice_language

    captions_payload = config.captions.model_dump(mode="json", by_alias=True, exclude_none=True)
    if captions_payload.get("enabled"):
        captions_payload["preset"] = normalize_caption_preset(captions_payload.get("preset"))

    return RenderRequest.model_validate(
        {
            "workflow": Workflow.IMAGE_STORY_TO_VIDEO.value,
            "webhookUrl": config.webhook_url,
            "source": config.source.model_dump(mode="json", by_alias=True, exclude_none=True),
            "media": {
                "type": MediaType.AI_VIDEO.value,
                "quality": "standard",
                "density": "medium",
            },
            "voice": voice_payload,
            "captions": captions_payload,
            "options": config.options.model_dump(mode="json", by_alias=True, exclude_none=True),
            "render": config.render.model_dump(mode="json", by_alias=True, exclude_none=True),
            "metadata": config.metadata,
            "aspectRatio": AspectRatio.NINE_SIXTEEN.value,
        }
    )


def normalize_editor_payload(config: RenderRequest) -> RenderRequest:
    if config.workflow == Workflow.IMAGE_STORY_TO_VIDEO:
        validate_rerender_image_story_config(config)
        return apply_rerender_defaults(config)
    validate_launch_config(config)
    return apply_launch_defaults(config)


def validate_rerender_image_story_config(config: RenderRequest) -> None:
    errors: list[str] = []

    if config.workflow != Workflow.IMAGE_STORY_TO_VIDEO:
        errors.append("Only image-story-to-video uses the editor image-story validation path.")

    if config.aspect_ratio not in {None, AspectRatio.NINE_SIXTEEN, "9:16"}:
        errors.append("Only 9:16 output is supported for image-story renders.")

    if config.captions.enabled and not config.voice.enabled:
        errors.append("Interactive captions require voice.enabled=true for image-story renders.")

    if config.captions.preset not in SUPPORTED_CAPTION_PRESETS:
        errors.append("Unsupported caption preset for image-story renders.")

    if config.render.resolution not in SUPPORTED_RESOLUTIONS:
        errors.append("Only 720p and 1080p are supported for image-story renders.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=errors,
        )


def apply_rerender_defaults(config: RenderRequest) -> RenderRequest:
    settings = get_settings()
    config.project_id = None

    if config.voice.enabled and not config.voice.voice_id:
        config.voice.voice_id = settings.default_voice_id
    if config.voice.enabled and not config.voice.language:
        config.voice.language = settings.default_voice_language
    if config.captions.enabled:
        config.captions.preset = normalize_caption_preset(config.captions.preset)
    if not config.aspect_ratio:
        config.aspect_ratio = AspectRatio.NINE_SIXTEEN

    return config

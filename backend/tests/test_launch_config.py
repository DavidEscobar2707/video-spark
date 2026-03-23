from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.schemas.render import AvatarRenderRequest, ImageStoryRenderRequest, RenderRequest
from app.services.launch import (
    apply_avatar_render_defaults,
    apply_image_story_defaults,
    apply_launch_defaults,
    validate_avatar_render_config,
    validate_image_story_render_config,
    validate_launch_config,
)


def test_launch_config_rejects_article_workflow():
    payload = RenderRequest.model_validate(
        {
            "workflow": "article-to-video",
            "source": {"url": "https://example.com/article"},
            "media": {"type": "ai-video", "quality": "pro"},
        }
    )

    with pytest.raises(HTTPException) as exc:
        validate_launch_config(payload)

    assert exc.value.status_code == 422
    assert "prompt-to-video and script-to-video" in str(exc.value.detail)


def test_launch_config_rejects_music_and_captions_without_voice():
    payload = RenderRequest.model_validate(
        {
            "workflow": "prompt-to-video",
            "source": {"prompt": "Create a short ad", "durationSeconds": 30},
            "media": {"type": "ai-video", "quality": "pro"},
            "captions": {"enabled": True},
            "voice": {"enabled": False},
            "music": {"enabled": True},
        }
    )

    with pytest.raises(HTTPException) as exc:
        validate_launch_config(payload)

    assert exc.value.status_code == 422
    detail = " ".join(exc.value.detail)
    assert "Interactive captions require voice.enabled=true" in detail
    assert "Music" in detail


def test_launch_config_accepts_karaoke_captions_with_voice():
    payload = RenderRequest.model_validate(
        {
            "workflow": "prompt-to-video",
            "source": {"prompt": "Create a short ad", "durationSeconds": 30},
            "media": {"type": "ai-video", "quality": "pro"},
            "voice": {"enabled": True},
            "captions": {"enabled": True, "preset": "karaoke"},
        }
    )

    validate_launch_config(payload)


def test_launch_config_accepts_new_caption_presets():
    payload = RenderRequest.model_validate(
        {
            "workflow": "prompt-to-video",
            "source": {"prompt": "Create a short ad", "durationSeconds": 30},
            "media": {"type": "ai-video", "quality": "pro"},
            "voice": {"enabled": True},
            "captions": {"enabled": True, "preset": "karaoke-bold", "position": "middle"},
        }
    )

    validate_launch_config(payload)


def test_apply_launch_defaults_sets_voice_and_caption_defaults():
    payload = RenderRequest.model_validate(
        {
            "workflow": "prompt-to-video",
            "source": {"prompt": "Create a short ad", "durationSeconds": 30},
            "media": {"type": "ai-video", "quality": "pro"},
            "voice": {"enabled": True},
            "captions": {"enabled": True},
        }
    )

    defaulted = apply_launch_defaults(payload)

    assert defaulted.voice.voice_id == "EXAVITQu4vr4xnSDxMaL"
    assert defaulted.voice.language == "en"
    assert defaulted.captions.preset == "karaoke-clean"


def test_launch_config_rejects_client_supplied_project_id():
    payload = RenderRequest.model_validate(
        {
            "workflow": "prompt-to-video",
            "projectId": "11111111-1111-1111-1111-111111111111",
            "source": {"prompt": "Create a short ad", "durationSeconds": 30},
            "media": {"type": "ai-video", "quality": "pro"},
            "voice": {"enabled": True},
        }
    )

    with pytest.raises(HTTPException) as exc:
        validate_launch_config(payload)

    assert exc.value.status_code == 422
    assert "projectId is server-managed" in " ".join(exc.value.detail)


def test_avatar_render_requires_configured_default_avatar(monkeypatch):
    monkeypatch.setenv("DEFAULT_AVATAR_IMAGE_URL", "")
    payload = AvatarRenderRequest.model_validate(
        {
            "source": {"text": "Deliver a short founder intro."},
        }
    )

    with pytest.raises(HTTPException) as exc:
        validate_avatar_render_config(payload)

    assert exc.value.status_code == 422
    assert "DEFAULT_AVATAR_IMAGE_URL" in " ".join(exc.value.detail)


def test_avatar_render_defaults_force_workflow_and_output(monkeypatch):
    monkeypatch.setenv("DEFAULT_AVATAR_IMAGE_URL", "https://example.com/avatar.png")
    payload = AvatarRenderRequest.model_validate(
        {
            "source": {"text": "Deliver a short founder intro.", "stylePrompt": "High-end startup ad"},
            "captions": {"enabled": False},
        }
    )

    validate_avatar_render_config(payload)
    defaulted = apply_avatar_render_defaults(payload)

    assert defaulted.workflow.value == "avatar-to-video"
    assert defaulted.media.type.value == "ai-video"
    assert defaulted.render.resolution.value == "720p"
    assert str(defaulted.aspect_ratio) == "9:16"
    assert defaulted.avatar is not None
    assert defaulted.avatar.enabled is True
    assert defaulted.avatar.url == "https://example.com/avatar.png"


def test_image_story_render_defaults_force_workflow_and_output():
    payload = ImageStoryRenderRequest.model_validate(
        {
            "source": {"prompt": "Launch a creator tool with a recurring hero", "durationSeconds": 25},
            "voice": {"enabled": True},
            "captions": {"enabled": True, "preset": "karaoke-pop"},
            "render": {"resolution": "1080p"},
        }
    )

    validate_image_story_render_config(payload)
    defaulted = apply_image_story_defaults(payload)

    assert defaulted.workflow.value == "image-story-to-video"
    assert defaulted.media.type.value == "ai-video"
    assert defaulted.voice.voice_id == "EXAVITQu4vr4xnSDxMaL"
    assert defaulted.captions.preset == "karaoke-pop"
    assert str(defaulted.aspect_ratio) == "9:16"

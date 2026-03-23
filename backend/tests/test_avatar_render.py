from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.render import AvatarRenderRequest
from app.services.launch import apply_avatar_render_defaults
from app.tasks.steps.script import split_avatar_scenes


def test_avatar_render_is_disabled():
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/avatar-render",
        json={
            "source": {"text": "Launch the product with a confident founder-style message."},
        },
    )

    assert response.status_code == 501
    assert "avatar-render is disabled for the MVP" in response.text


def test_avatar_render_docs_report_disabled():
    client = TestClient(create_app())

    response = client.get("/api/v1/avatar-render")

    assert response.status_code == 200
    assert response.json()["status"] == "disabled"


def test_avatar_render_defaults_keep_avatar_scenes_silent(monkeypatch):
    monkeypatch.setenv("DEFAULT_AVATAR_IMAGE_URL", "https://example.com/avatar.png")

    payload = AvatarRenderRequest.model_validate(
        {
            "source": {"text": "Launch the product with a confident founder-style message."},
        }
    )

    render_payload = apply_avatar_render_defaults(payload)

    assert render_payload.voice.enabled is False


def test_avatar_scene_planner_disables_native_audio(monkeypatch):
    monkeypatch.setenv("DEFAULT_AVATAR_IMAGE_URL", "https://example.com/avatar.png")

    payload = AvatarRenderRequest.model_validate(
        {
            "source": {"text": "Launch the product with a confident founder-style message."},
        }
    )
    render_payload = apply_avatar_render_defaults(payload)

    scenes = asyncio.run(
        split_avatar_scenes("Launch the product with a confident founder-style message.", render_payload)
    )

    assert len(scenes) == 3
    assert all(scene["generateAudio"] is False for scene in scenes)

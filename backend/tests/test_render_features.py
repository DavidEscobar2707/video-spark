from __future__ import annotations

import pytest

from app import dependencies
from app.schemas.render import VoiceListResponse
from app.routes import render as render_routes


@pytest.fixture(autouse=True)
def bypass_workspace_lookup(monkeypatch):
    monkeypatch.setattr(dependencies, "ensure_user_workspace", lambda user: user)


def test_get_voices_returns_backend_catalog(client, monkeypatch):
    async def fake_list_available_voices():
        return VoiceListResponse.model_validate(
            {
                "voices": [
                    {
                        "voiceId": "voice-1",
                        "name": "Sarah",
                        "language": "en",
                        "labels": {"gender": "female"},
                        "previewAudioUrl": "https://example.com/preview.mp3",
                        "thumbnailUrl": "data:image/svg+xml,test",
                        "isDefault": True,
                    }
                ]
            }
        )

    monkeypatch.setattr(render_routes, "list_available_voices", fake_list_available_voices)

    response = client.get("/api/v1/voices")

    assert response.status_code == 200
    body = response.json()
    assert body["voices"][0]["voiceId"] == "voice-1"
    assert body["voices"][0]["isDefault"] is True


def test_get_caption_presets_returns_supported_presets(client):
    response = client.get("/api/v1/caption-presets")

    assert response.status_code == 200
    preset_ids = [preset["id"] for preset in response.json()["presets"]]
    assert preset_ids == ["karaoke-bold", "karaoke-clean", "karaoke-pop"]


def test_generate_script_returns_structured_payload(client):
    response = client.post(
        "/api/v1/generate-script",
        json={
            "prompt": "a premium creator ad for a video automation app",
            "tone": "sharp and persuasive",
            "targetDurationSeconds": 20,
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"]
    assert payload["hook"]
    assert payload["script"]
    assert len(payload["sceneBeats"]) == 4


def test_image_story_render_creates_job_with_server_defaults(client, monkeypatch):
    captured: dict[str, object] = {}

    async def fake_create_render_job(user, payload, credits):
        captured["user"] = user
        captured["payload"] = payload
        captured["credits"] = credits
        return {"project_id": "story-project-id"}

    monkeypatch.setattr(render_routes, "create_render_job", fake_create_render_job)

    response = client.post(
        "/api/v1/image-story-render",
        json={
            "source": {"prompt": "Tell a five-scene launch story", "durationSeconds": 25},
            "voice": {"enabled": True},
            "captions": {"enabled": True, "position": "middle", "preset": "karaoke-pop"},
            "render": {"resolution": "1080p"},
        },
    )

    assert response.status_code == 200
    assert response.json()["pid"] == "story-project-id"
    assert response.json()["workflow"] == "image-story-to-video"
    payload = captured["payload"]
    assert payload.workflow.value == "image-story-to-video"
    assert payload.captions.preset == "karaoke-pop"
    assert str(payload.aspect_ratio) == "9:16"
    assert payload.voice.voice_id == "EXAVITQu4vr4xnSDxMaL"

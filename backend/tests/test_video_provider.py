from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.services.video_provider import GeminiVeoVideoProvider


class _FakeVideoFile:
    def __init__(self) -> None:
        self.saved_path: str | None = None

    def save(self, path: str) -> None:
        self.saved_path = path
        Path(path).write_bytes(b"fake-mp4")


class _FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_videos(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(name="operations/scene-0", done=False)


class _FakeOperations:
    def get(self, operation):
        video_file = _FakeVideoFile()
        generated_video = SimpleNamespace(video=video_file)
        response = SimpleNamespace(generated_videos=[generated_video])
        return SimpleNamespace(name=operation.name, done=True, response=response, error=None)


class _FakeFiles:
    def __init__(self) -> None:
        self.download_calls = 0

    def download(self, *, file):
        self.download_calls += 1
        return file


class _FakeClient:
    def __init__(self) -> None:
        self.models = _FakeModels()
        self.operations = _FakeOperations()
        self.files = _FakeFiles()


class _FallbackModels(_FakeModels):
    def generate_videos(self, **kwargs):
        self.calls.append(kwargs)
        if "generate_audio" in kwargs["config"].model_dump(exclude_none=True):
            raise RuntimeError("generate_audio parameter is not supported in Gemini API.")
        return SimpleNamespace(name="operations/scene-0", done=False)


class _FallbackClient(_FakeClient):
    def __init__(self) -> None:
        self.models = _FallbackModels()
        self.operations = _FakeOperations()
        self.files = _FakeFiles()


@pytest.mark.asyncio
async def test_gemini_provider_generates_local_clip(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    settings = get_settings()
    fake_client = _FakeClient()
    provider = GeminiVeoVideoProvider(
        client_factory=lambda _settings: fake_client,
        settings_factory=lambda: settings,
    )

    operation = await provider.start_scene_clip(
        {
            "text": "A fast product shot",
            "visualPrompt": "Cinematic product ad",
            "durationSeconds": 5,
        },
        {"jobId": "job-123", "sceneIndex": 0, "resolution": "720p", "aspectRatio": "9:16"},
    )
    result = await provider.poll_scene_clip(
        operation,
        {"jobId": "job-123", "sceneIndex": 0, "resolution": "720p", "aspectRatio": "9:16"},
    )

    assert operation.external_ref == "operations/scene-0"
    assert result.clip_path is not None
    assert Path(result.clip_path).exists()
    assert fake_client.files.download_calls == 1
    call = fake_client.models.calls[0]
    assert call["model"] == settings.video_provider_model
    assert call["config"].aspect_ratio == "9:16"
    assert call["config"].resolution == "720p"
    assert call["config"].duration_seconds == 4
    assert "person_generation" not in call["config"].model_dump(exclude_none=True)


@pytest.mark.asyncio
async def test_gemini_provider_passes_reference_image_and_audio_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    settings = get_settings()
    fake_client = _FakeClient()
    provider = GeminiVeoVideoProvider(
        client_factory=lambda _settings: fake_client,
        settings_factory=lambda: settings,
    )

    reference_image = tmp_path / "avatar.png"
    reference_image.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    await provider.start_scene_clip(
        {
            "text": "Introduce the product confidently.",
            "spokenText": "Introduce the product confidently.",
            "visualPrompt": "Confident founder talking head",
            "durationSeconds": 6,
            "generateAudio": True,
            "referenceImageUrl": reference_image.as_posix(),
            "referenceImageMimeType": "image/png",
            "referenceType": "ASSET",
            "shotType": "talking-head",
        },
        {"jobId": "job-avatar", "sceneIndex": 0, "resolution": "720p", "aspectRatio": "9:16"},
    )

    call = fake_client.models.calls[0]
    assert call["config"].generate_audio is True
    assert call["config"].reference_images is not None
    assert len(call["config"].reference_images) == 1
    assert call["config"].reference_images[0].reference_type.value == "ASSET"
    assert call["config"].reference_images[0].image.mime_type == "image/png"
    assert "says exactly" in call["prompt"]


@pytest.mark.asyncio
async def test_gemini_provider_retries_without_audio_when_gemini_api_rejects_it(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    settings = get_settings()
    fake_client = _FallbackClient()
    provider = GeminiVeoVideoProvider(
        client_factory=lambda _settings: fake_client,
        settings_factory=lambda: settings,
    )

    reference_image = tmp_path / "avatar.png"
    reference_image.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    operation = await provider.start_scene_clip(
        {
            "text": "Introduce the product confidently.",
            "spokenText": "Introduce the product confidently.",
            "visualPrompt": "Confident founder talking head",
            "durationSeconds": 6,
            "generateAudio": True,
            "referenceImageUrl": reference_image.as_posix(),
            "referenceImageMimeType": "image/png",
            "referenceType": "ASSET",
            "shotType": "talking-head",
        },
        {"jobId": "job-avatar", "sceneIndex": 0, "resolution": "720p", "aspectRatio": "9:16"},
    )

    assert operation.external_ref == "operations/scene-0"
    assert len(fake_client.models.calls) == 2
    assert fake_client.models.calls[0]["config"].generate_audio is True
    assert "generate_audio" not in fake_client.models.calls[1]["config"].model_dump(exclude_none=True)


@pytest.mark.asyncio
async def test_gemini_provider_omits_generate_audio_when_scene_does_not_request_it(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    settings = get_settings()
    fake_client = _FakeClient()
    provider = GeminiVeoVideoProvider(
        client_factory=lambda _settings: fake_client,
        settings_factory=lambda: settings,
    )

    await provider.start_scene_clip(
        {
            "text": "Show the founder walking through a modern studio.",
            "visualPrompt": "Premium founder b-roll",
            "durationSeconds": 6,
            "generateAudio": False,
            "shotType": "supporting",
        },
        {"jobId": "job-avatar", "sceneIndex": 1, "resolution": "720p", "aspectRatio": "9:16"},
    )

    call = fake_client.models.calls[0]
    assert "generate_audio" not in call["config"].model_dump(exclude_none=True)


@pytest.mark.live_veo
@pytest.mark.asyncio
async def test_live_veo_generates_real_clip(tmp_path, monkeypatch):
    if os.getenv("RUN_LIVE_VEO_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_VEO_TESTS=1 to hit the real Veo API.")
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your-gemini-api-key":
        pytest.skip("A real GEMINI_API_KEY is required for the live Veo smoke test.")

    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    settings = get_settings()
    provider = GeminiVeoVideoProvider(settings_factory=lambda: settings)

    operation = await provider.start_scene_clip(
        {
            "text": "A close-up of pizza dough stretching in a warm kitchen",
            "visualPrompt": "Handheld cinematic cooking shot",
            "durationSeconds": 4,
        },
        {"jobId": "live-veo", "sceneIndex": 0, "resolution": "720p", "aspectRatio": "9:16"},
    )
    result = await provider.poll_scene_clip(
        operation,
        {"jobId": "live-veo", "sceneIndex": 0, "resolution": "720p", "aspectRatio": "9:16"},
    )

    assert result.clip_path is not None
    clip_path = Path(result.clip_path)
    assert clip_path.exists()
    assert clip_path.suffix == ".mp4"
    assert clip_path.stat().st_size > 0

from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

from app.tasks.steps import voice as voice_step


class _FakeResponse:
    def __init__(self, payload: dict, headers: dict[str, str] | None = None, status_code: int = 200) -> None:
        self._payload = payload
        self.headers = headers or {}
        self.status_code = status_code
        self.text = "ok"

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_generate_voice_writes_audio_and_alignment(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    async def fake_request_with_retry(method, url, **kwargs):
        _ = method
        _ = url
        _ = kwargs
        return _FakeResponse(
            {
                "audio_base64": base64.b64encode(b"voice-data").decode(),
                "alignment": {
                    "characters": list("Hola"),
                    "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3],
                    "character_end_times_seconds": [0.08, 0.18, 0.28, 0.38],
                },
            },
            headers={"request-id": "req_123"},
        )

    monkeypatch.setattr(voice_step, "request_with_retry", fake_request_with_retry)

    artifact = await voice_step.generate_voice(
        "Hola",
        {"enabled": True, "voiceId": "voice_123", "language": "es"},
        {"jobId": "job-voice"},
    )

    assert artifact is not None
    assert artifact["requestId"] == "req_123"
    audio_path = Path(artifact["audioPath"])
    assert audio_path.exists()
    assert audio_path.read_bytes() == b"voice-data"


@pytest.mark.asyncio
async def test_generate_voice_uses_default_voice_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    captured_payload: dict[str, object] = {}

    async def fake_request_with_retry(method, url, **kwargs):
        _ = method
        captured_payload["url"] = url
        captured_payload["json"] = kwargs["json"]
        return _FakeResponse(
            {
                "audio_base64": base64.b64encode(b"voice-data").decode(),
                "alignment": {
                    "characters": list("Hola"),
                    "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3],
                    "character_end_times_seconds": [0.08, 0.18, 0.28, 0.38],
                },
            }
        )

    monkeypatch.setattr(voice_step, "request_with_retry", fake_request_with_retry)

    artifact = await voice_step.generate_voice(
        "Hola",
        {"enabled": True},
        {"jobId": "job-voice-default"},
    )

    assert artifact is not None
    assert artifact["voiceId"] == "EXAVITQu4vr4xnSDxMaL"
    assert captured_payload["json"]["language_code"] == "en"
    assert "EXAVITQu4vr4xnSDxMaL" in captured_payload["url"]


@pytest.mark.live_elevenlabs
@pytest.mark.asyncio
async def test_live_elevenlabs_generates_real_voice(monkeypatch, tmp_path):
    if os.getenv("RUN_LIVE_ELEVENLABS_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_ELEVENLABS_TESTS=1 to hit the real ElevenLabs API.")
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("A real ELEVENLABS_API_KEY is required for the live ElevenLabs smoke test.")
    if not os.getenv("ELEVENLABS_TEST_VOICE_ID"):
        pytest.skip("Set ELEVENLABS_TEST_VOICE_ID to a valid ElevenLabs voice id.")

    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))

    artifact = await voice_step.generate_voice(
        "Hola, este es un test corto de narracion.",
        {
            "enabled": True,
            "voiceId": os.getenv("ELEVENLABS_TEST_VOICE_ID"),
            "language": "es",
            "stability": 0.4,
        },
        {"jobId": "live-voice"},
    )

    assert artifact is not None
    assert Path(artifact["audioPath"]).exists()
    assert Path(artifact["audioPath"]).stat().st_size > 0
    assert artifact["alignment"]["characters"]

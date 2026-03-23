from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.services import image_provider


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = "ok") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_generate_story_image_uses_supported_portrait_size(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("IMAGE_GENERATION_TIMEOUT_SECONDS", "240")

    captured: dict[str, object] = {}

    async def fake_request_with_retry(method, url, **kwargs):
        _ = method
        _ = url
        captured["json"] = kwargs["json"]
        captured["timeout"] = kwargs["timeout"]
        return _FakeResponse({"data": [{"b64_json": base64.b64encode(b"png-bytes").decode()}]})

    monkeypatch.setattr(image_provider, "request_with_retry", fake_request_with_retry)

    artifact = await image_provider.OpenAIImageProvider().generate_story_image(
        "A premium vertical story frame",
        {"jobId": "image-job", "imageIndex": 0},
    )

    assert captured["json"]["size"] == "1024x1536"
    assert int(captured["timeout"].read) == 240
    assert Path(artifact.image_path).exists()
    assert Path(artifact.image_path).read_bytes() == b"png-bytes"


@pytest.mark.asyncio
async def test_generate_story_image_surfaces_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("IMAGE_GENERATION_TIMEOUT_SECONDS", "180")

    async def fake_request_with_retry(method, url, **kwargs):
        _ = method
        _ = url
        _ = kwargs
        raise image_provider.httpx.ReadTimeout("timed out")

    monkeypatch.setattr(image_provider, "request_with_retry", fake_request_with_retry)

    with pytest.raises(image_provider.ExternalServiceError) as exc:
        await image_provider.OpenAIImageProvider().generate_story_image(
            "A premium vertical story frame",
            {"jobId": "image-job", "imageIndex": 0},
        )

    assert "timed out after 180 seconds" in str(exc.value)

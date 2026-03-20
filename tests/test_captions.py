from __future__ import annotations

from pathlib import Path

import pytest

from app.tasks.steps.captions import build_captions


@pytest.mark.asyncio
async def test_build_captions_writes_ass_and_srt(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))

    voice_artifact = {
        "alignment": {
            "characters": list("Hola mundo"),
            "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.7, 0.8, 0.9, 1.0],
            "character_end_times_seconds": [0.08, 0.18, 0.28, 0.38, 0.52, 0.68, 0.78, 0.88, 0.98, 1.08],
        }
    }

    result = await build_captions(
        voice_artifact,
        {"enabled": True, "preset": "karaoke", "position": "bottom"},
        {"jobId": "job-captions"},
    )

    assert result is not None
    ass_path = Path(result["assPath"])
    srt_path = Path(result["srtPath"])
    assert ass_path.exists()
    assert srt_path.exists()
    assert "{\\k" in ass_path.read_text(encoding="utf-8")
    assert "Hola mundo" in srt_path.read_text(encoding="utf-8")

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.services.ffmpeg_svc import probe_media
from app.tasks.steps.compose import compose_video


async def _run_command(*command: str) -> None:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise AssertionError(stderr.decode().strip())


@pytest.mark.asyncio
async def test_compose_video_creates_local_mp4_with_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))

    clip_a = tmp_path / "clip-a.mp4"
    clip_b = tmp_path / "clip-b.mp4"
    voice_track = tmp_path / "voice.mp3"

    await _run_command(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:s=540x960:d=1",
        "-pix_fmt",
        "yuv420p",
        clip_a.as_posix(),
    )
    await _run_command(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=540x960:d=1",
        "-pix_fmt",
        "yuv420p",
        clip_b.as_posix(),
    )
    await _run_command(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=2",
        voice_track.as_posix(),
    )

    subtitle_ass = tmp_path / "captions.ass"
    subtitle_ass.write_text(
        """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,54,&H00FFD966,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,0,2,60,60,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Karaoke,,0,0,0,,{\\k100}Hola {\\k100}mundo
""",
        encoding="utf-8",
    )

    output_path = await compose_video(
        scenes=[{"text": "scene a"}, {"text": "scene b"}],
        media_urls=[clip_a.as_posix(), clip_b.as_posix()],
        voice_url=voice_track.as_posix(),
        subtitle_ass_path=subtitle_ass.as_posix(),
        config={"jobId": "compose-audio"},
    )

    final_path = Path(output_path)
    assert final_path.exists()

    metadata = await probe_media(final_path)
    codec_types = {stream["codec_type"] for stream in metadata["streams"]}
    assert "video" in codec_types
    assert "audio" in codec_types


@pytest.mark.asyncio
async def test_compose_video_can_output_silent_mp4(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))

    clip_a = tmp_path / "clip-a.mp4"
    await _run_command(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=green:s=540x960:d=1",
        "-pix_fmt",
        "yuv420p",
        clip_a.as_posix(),
    )

    output_path = await compose_video(
        scenes=[{"text": "scene a"}],
        media_urls=[clip_a.as_posix()],
        voice_url=None,
        subtitle_ass_path=None,
        config={"jobId": "compose-silent"},
    )

    metadata = await probe_media(Path(output_path))
    codec_types = {stream["codec_type"] for stream in metadata["streams"]}
    assert codec_types == {"video"}


@pytest.mark.asyncio
async def test_compose_video_can_preserve_clip_audio(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKER_ARTIFACTS_DIR", str(tmp_path))

    clip_a = tmp_path / "clip-a.mp4"
    clip_b = tmp_path / "clip-b.mp4"
    await _run_command(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=yellow:s=540x960:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=660:duration=1",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        clip_a.as_posix(),
    )
    await _run_command(
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=purple:s=540x960:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=1",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        clip_b.as_posix(),
    )

    output_path = await compose_video(
        scenes=[{"text": "scene a"}, {"text": "scene b"}],
        media_urls=[clip_a.as_posix(), clip_b.as_posix()],
        voice_url=None,
        subtitle_ass_path=None,
        config={"jobId": "compose-native-audio", "preserveClipAudio": True},
    )

    metadata = await probe_media(Path(output_path))
    codec_types = {stream["codec_type"] for stream in metadata["streams"]}
    assert "video" in codec_types
    assert "audio" in codec_types

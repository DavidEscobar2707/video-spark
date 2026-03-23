from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings
from app.services.ffmpeg_svc import (
    burn_subtitles_command,
    concat_command,
    normalize_clip_command,
    run_media_command,
)
from app.utils.http import get_async_client


async def _materialize_audio_track(voice_url: str, job_dir: Path) -> Path:
    parsed = urlparse(voice_url)
    audio_dir = job_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    destination = audio_dir / "voice-track.mp3"

    if parsed.scheme in {"http", "https"}:
        response = await get_async_client().get(voice_url)
        response.raise_for_status()
        destination.write_bytes(response.content)
        return destination

    source_path = Path(voice_url)
    if source_path.exists():
        destination.write_bytes(source_path.read_bytes())
        return destination

    raise FileNotFoundError(f"Voice track was not found at {voice_url}.")


async def compose_video(
    scenes: list[dict[str, object]],
    media_urls: list[str],
    voice_url: str | None,
    subtitle_ass_path: str | None,
    config: dict,
) -> str:
    """Normalize generated clips and concatenate them into a single local mp4 artifact."""

    _ = scenes  # Scenes will matter once captions and image inserts are added.
    settings = get_settings()
    preserve_clip_audio = bool(config.get("preserveClipAudio")) and voice_url is None
    job_dir = Path(settings.worker_artifacts_dir) / str(config.get("jobId") or "job")
    normalized_dir = job_dir / "normalized"
    final_dir = job_dir / "final"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    normalized_clips: list[Path] = []
    for index, media_url in enumerate(media_urls):
        source_path = Path(media_url)
        output_path = normalized_dir / f"scene-{index:02d}.mp4"
        await run_media_command(
            normalize_clip_command(source_path, output_path, strip_audio=not preserve_clip_audio)
        )
        normalized_clips.append(output_path)

    concat_file_path = job_dir / "clips.txt"
    concat_file_path.write_text(
        "".join(f"file '{clip.as_posix()}'\n" for clip in normalized_clips),
        encoding="utf-8",
    )

    voice_track_path = await _materialize_audio_track(voice_url, job_dir) if voice_url else None
    assembled_output_path = final_dir / "assembled.mp4"
    await run_media_command(
        concat_command(
            concat_file_path,
            voice_track_path,
            assembled_output_path,
            preserve_clip_audio=preserve_clip_audio,
        )
    )

    if subtitle_ass_path:
        final_output_path = final_dir / "final.mp4"
        await run_media_command(
            burn_subtitles_command(assembled_output_path, Path(subtitle_ass_path), final_output_path)
        )
        return final_output_path.as_posix()

    return assembled_output_path.as_posix()

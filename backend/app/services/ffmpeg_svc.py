from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import get_settings
from app.utils.errors import PipelineStepError


def ffmpeg_bin() -> str:
    return get_settings().ffmpeg_bin


def ffprobe_bin() -> str:
    return get_settings().ffprobe_bin


def normalize_clip_command(source_path: Path, output_path: Path, *, strip_audio: bool = True) -> list[str]:
    command = [
        ffmpeg_bin(),
        "-y",
        "-i",
        str(source_path),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
    ]
    if strip_audio:
        command.extend(["-an"])
    else:
        command.extend(["-c:a", "aac", "-ar", "44100", "-ac", "2"])
    command.append(str(output_path))
    return command


def image_segment_command(source_path: Path, output_path: Path, *, duration_seconds: float) -> list[str]:
    frame_count = max(1, int(round(duration_seconds * 30)))
    zoom_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0008,1.12)':d={frame_count}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,"
        "format=yuv420p"
    )
    return [
        ffmpeg_bin(),
        "-y",
        "-loop",
        "1",
        "-i",
        str(source_path),
        "-vf",
        zoom_filter,
        "-t",
        str(duration_seconds),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]


def concat_command(
    file_list_path: Path,
    voice_track_path: Path | None,
    output_path: Path,
    *,
    preserve_clip_audio: bool = False,
) -> list[str]:
    command = [
        ffmpeg_bin(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(file_list_path),
    ]
    if voice_track_path is not None:
        command.extend(
            [
                "-i",
                str(voice_track_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
            ]
        )
    elif preserve_clip_audio:
        command.extend(["-map", "0:v:0", "-map", "0:a:0?"])
    else:
        command.extend(["-map", "0:v:0", "-an"])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
        ]
    )
    if voice_track_path is not None or preserve_clip_audio:
        command.extend(["-c:a", "aac"])
    command.append(str(output_path))
    return command


def burn_subtitles_command(source_path: Path, subtitle_ass_path: Path, output_path: Path) -> list[str]:
    filter_path = subtitle_ass_path.as_posix().replace(":", r"\:").replace("'", r"\'")
    return [
        ffmpeg_bin(),
        "-y",
        "-i",
        str(source_path),
        "-vf",
        f"ass='{filter_path}'",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


async def run_media_command(command: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise PipelineStepError(
            f"Media command failed: {' '.join(command)}\n{stderr.decode().strip() or stdout.decode().strip()}"
        )


async def probe_media(path: Path) -> dict[str, object]:
    process = await asyncio.create_subprocess_exec(
        ffprobe_bin(),
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise PipelineStepError(f"ffprobe failed for {path}: {stderr.decode().strip()}")
    return json.loads(stdout.decode())

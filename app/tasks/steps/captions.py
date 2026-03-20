from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.utils.errors import PipelineStepError


@dataclass(slots=True)
class WordTiming:
    text: str
    start: float
    end: float


@dataclass(slots=True)
class CaptionChunk:
    words: list[WordTiming]
    start: float
    end: float
    text: str


def _job_dir(job_id: str) -> Path:
    settings = get_settings()
    path = Path(settings.worker_artifacts_dir) / job_id / "captions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def _ass_timestamp(seconds: float) -> str:
    centiseconds_total = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds_total, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, centiseconds = divmod(remainder, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _alignment_position(position: str | None) -> int:
    return {"top": 8, "middle": 5, "bottom": 2}.get(position or "bottom", 2)


def _extract_words(alignment: dict[str, Any]) -> list[WordTiming]:
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if not chars or len(chars) != len(starts) or len(chars) != len(ends):
        raise PipelineStepError("ElevenLabs alignment payload is malformed.")

    words: list[WordTiming] = []
    current_chars: list[str] = []
    current_start: float | None = None
    current_end: float | None = None

    for char, start, end in zip(chars, starts, ends, strict=False):
        if str(char).isspace():
            if current_chars and current_start is not None and current_end is not None:
                words.append(WordTiming("".join(current_chars), float(current_start), float(current_end)))
            current_chars = []
            current_start = None
            current_end = None
            continue

        if current_start is None:
            current_start = float(start)
        current_chars.append(str(char))
        current_end = float(end)

    if current_chars and current_start is not None and current_end is not None:
        words.append(WordTiming("".join(current_chars), float(current_start), float(current_end)))

    if not words:
        raise PipelineStepError("Could not derive subtitle words from ElevenLabs alignment.")
    return words


def _chunk_words(words: list[WordTiming], *, max_words: int = 4, max_duration: float = 2.4) -> list[CaptionChunk]:
    chunks: list[CaptionChunk] = []
    current: list[WordTiming] = []

    for word in words:
        proposed = current + [word]
        duration = proposed[-1].end - proposed[0].start
        if current and (len(proposed) > max_words or duration > max_duration):
            chunks.append(
                CaptionChunk(
                    words=current,
                    start=current[0].start,
                    end=current[-1].end,
                    text=" ".join(item.text for item in current),
                )
            )
            current = [word]
            continue
        current = proposed

    if current:
        chunks.append(
            CaptionChunk(
                words=current,
                start=current[0].start,
                end=current[-1].end,
                text=" ".join(item.text for item in current),
            )
        )
    return chunks


def _build_srt(chunks: list[CaptionChunk]) -> str:
    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        lines.extend(
            [
                str(index),
                f"{_srt_timestamp(chunk.start)} --> {_srt_timestamp(chunk.end)}",
                chunk.text,
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _build_ass(chunks: list[CaptionChunk], *, position: str | None) -> str:
    alignment = _alignment_position(position)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,58,&H00FFD966,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,0,{alignment},60,60,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines: list[str] = [header]
    for chunk in chunks:
        karaoke_parts: list[str] = []
        for word in chunk.words:
            duration_cs = max(1, int(round((word.end - word.start) * 100)))
            karaoke_parts.append(f"{{\\k{duration_cs}}}{word.text}")
        karaoke_text = " ".join(karaoke_parts)
        lines.append(
            "Dialogue: 0,"
            f"{_ass_timestamp(chunk.start)},{_ass_timestamp(chunk.end)},Karaoke,,0,0,0,,"
            f"{karaoke_text}"
        )
    return "\n".join(lines).strip() + "\n"


async def build_captions(
    voice_artifact: dict[str, Any] | None,
    captions_config: dict[str, Any],
    runtime_config: dict[str, object],
) -> dict[str, str] | None:
    """Build editable subtitle sidecars from ElevenLabs alignment data."""

    if not captions_config.get("enabled"):
        return None
    if voice_artifact is None:
        raise PipelineStepError("Interactive captions require a generated voice track.")

    preset = captions_config.get("preset") or "karaoke-social"
    if preset not in {"karaoke", "karaoke-social"}:
        raise PipelineStepError(f"Unsupported caption preset: {preset}")

    words = _extract_words(voice_artifact["alignment"])
    chunks = _chunk_words(words)
    job_dir = _job_dir(str(runtime_config.get("jobId") or "job"))
    ass_path = job_dir / "captions.ass"
    srt_path = job_dir / "captions.srt"
    ass_path.write_text(_build_ass(chunks, position=captions_config.get("position")), encoding="utf-8")
    srt_path.write_text(_build_srt(chunks), encoding="utf-8")
    return {"assPath": ass_path.as_posix(), "srtPath": srt_path.as_posix(), "preset": preset}

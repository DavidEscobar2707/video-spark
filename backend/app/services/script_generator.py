from __future__ import annotations

import re

from app.schemas.render import ScriptBeat, ScriptGenerationRequest, ScriptGenerationResponse


def _compact_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _title_from_prompt(prompt: str) -> str:
    words = [word for word in re.findall(r"[A-Za-z0-9']+", prompt) if word]
    if not words:
        return "Untitled Script"
    return " ".join(words[:6]).title()


def build_script_suggestion(request: ScriptGenerationRequest) -> ScriptGenerationResponse:
    prompt = _compact_sentence(request.prompt)
    tone = _compact_sentence(request.tone or "confident, modern, persuasive")
    duration = request.target_duration_seconds or 20
    language = (request.language or "en").strip()

    hook = f"Stop scrolling: {prompt.lower().rstrip('.')}."
    value = (
        f"Explain the core promise clearly in a {tone.lower()} tone and make it feel designed for a {duration}-second vertical video."
    )
    proof = "Show one concrete proof point, transformation, or benefit the viewer can picture instantly."
    cta = "Close with a direct call to action that makes the next step feel obvious."

    script_lines = [hook, value, proof, cta]
    scene_beats = [
        ScriptBeat(label="Hook", text=hook),
        ScriptBeat(label="Value", text=value),
        ScriptBeat(label="Proof", text=proof),
        ScriptBeat(label="CTA", text=cta),
    ]

    if language.lower() != "en":
        script_lines.append(f"Language note: adapt the final voiceover naturally for {language}.")

    return ScriptGenerationResponse(
        title=_title_from_prompt(prompt),
        hook=hook,
        script="\n".join(script_lines),
        sceneBeats=scene_beats,
    )

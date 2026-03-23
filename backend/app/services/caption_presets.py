from __future__ import annotations

from typing import Any


_PRESET_SPECS: dict[str, dict[str, Any]] = {
    "karaoke-bold": {
        "id": "karaoke-bold",
        "name": "Karaoke Bold",
        "description": "Large high-contrast captions with strong outline and active-word highlight.",
        "fontName": "Arial",
        "fontSize": 64,
        "primaryColour": "&H0000F5FF",
        "secondaryColour": "&H00FFFFFF",
        "outlineColour": "&H00000000",
        "backColour": "&H78000000",
        "outline": 5,
        "shadow": 1,
        "bold": 1,
        "spacing": 0,
        "marginV": 110,
    },
    "karaoke-clean": {
        "id": "karaoke-clean",
        "name": "Karaoke Clean",
        "description": "Balanced editorial captions for most brand videos.",
        "fontName": "Arial",
        "fontSize": 58,
        "primaryColour": "&H00FFD966",
        "secondaryColour": "&H00FFFFFF",
        "outlineColour": "&H00000000",
        "backColour": "&H64000000",
        "outline": 4,
        "shadow": 0,
        "bold": 1,
        "spacing": 0,
        "marginV": 90,
    },
    "karaoke-pop": {
        "id": "karaoke-pop",
        "name": "Karaoke Pop",
        "description": "Punchier social-style captions with brighter highlight and tighter layout.",
        "fontName": "Arial",
        "fontSize": 60,
        "primaryColour": "&H0039FF84",
        "secondaryColour": "&H00FFFFFF",
        "outlineColour": "&H000F0F0F",
        "backColour": "&H70000000",
        "outline": 3,
        "shadow": 0,
        "bold": 1,
        "spacing": 1,
        "marginV": 100,
    },
}

_PRESET_ALIASES = {
    None: "karaoke-clean",
    "": "karaoke-clean",
    "karaoke": "karaoke-clean",
    "karaoke-social": "karaoke-pop",
}


def normalize_caption_preset(preset: str | None) -> str:
    normalized = _PRESET_ALIASES.get(preset, preset)
    if normalized not in _PRESET_SPECS:
        raise ValueError(f"Unsupported caption preset: {preset}")
    return str(normalized)


def get_caption_preset_spec(preset: str | None) -> dict[str, Any]:
    return dict(_PRESET_SPECS[normalize_caption_preset(preset)])


def list_caption_presets() -> list[dict[str, Any]]:
    return [dict(spec) for spec in _PRESET_SPECS.values()]

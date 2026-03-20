from __future__ import annotations

from app.schemas.render import RenderRequest
from app.services.credits import calculate_credits


def test_calculate_credits_for_prompt_to_video_ai_video_ultra():
    payload = RenderRequest.model_validate(
        {
            "workflow": "prompt-to-video",
            "source": {"prompt": "Create an ad", "durationSeconds": 40},
            "media": {"type": "ai-video", "quality": "ultra"},
            "voice": {"enabled": True},
        }
    )

    assert calculate_credits(payload) == 39


def test_calculate_credits_for_script_to_video_moving_image_pro():
    payload = RenderRequest.model_validate(
        {
            "workflow": "script-to-video",
            "source": {"text": "Narration"},
            "media": {"type": "ai-video", "quality": "pro"},
            "voice": {"enabled": True},
        }
    )

    assert calculate_credits(payload) == 15

from __future__ import annotations

import math

from app.schemas.render import RenderRequest


def _resolved_duration(config: RenderRequest) -> float:
    return (
        config.source.duration_seconds
        or config.options.prompt_target_duration
        or config.options.target_duration
        or 30
    )


def calculate_credits(config: RenderRequest) -> int:
    base_cost = {
        "script-to-video": 3,
        "prompt-to-video": 5,
    }
    media_multiplier = {
        "ai-video": 3,
        "video": 3,
    }
    quality_multiplier = {
        "standard": 1,
        "pro": 1.5,
        "ultra": 2.5,
    }

    credits = base_cost.get(config.workflow.value, 3)
    credits *= media_multiplier.get(config.media.type.value, 1)
    if config.media.quality:
        credits *= quality_multiplier.get(config.media.quality.value, 1)

    duration = _resolved_duration(config)
    credits += max(0, math.floor((duration - 30) / 30)) * 3

    if config.voice.enabled:
        credits += 1

    return math.ceil(credits)


async def deduct_credits(tenant_id: str, amount: int, *, reason: str) -> dict[str, object]:
    return {"tenant_id": tenant_id, "amount": amount, "reason": reason, "status": "deducted"}


async def refund_credits(tenant_id: str, amount: int, *, reason: str) -> dict[str, object]:
    return {"tenant_id": tenant_id, "amount": amount, "reason": reason, "status": "refunded"}

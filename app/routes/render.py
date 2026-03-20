from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.supabase import AuthenticatedUser
from app.dependencies import get_current_user_or_api_key
from app.schemas.render import AvatarRenderRequest, CreditEstimateResponse, RenderRequest, RenderSuccessResponse
from app.services.credits import calculate_credits
from app.services.job_queue import create_render_job
from app.services.launch import apply_launch_defaults, validate_launch_config

router = APIRouter()


@router.get("/render")
async def get_render_docs() -> dict[str, object]:
    return {
        "name": "VideoSpark Render API",
        "auth": "supabase-jwt",
        "launchWorkflows": ["script-to-video", "prompt-to-video"],
        "launchMedia": ["ai-video"],
        "unsupportedAtLaunch": [
            "article-to-video",
            "moving-image",
            "music",
            "payments",
            "team",
            "avatar-to-video",
        ],
        "defaults": {
            "voiceId": "EXAVITQu4vr4xnSDxMaL",
            "voiceModel": "eleven_multilingual_v2",
            "voiceLanguage": "en",
            "captionsPreset": "karaoke",
        },
        "projectId": "server-generated",
        "status": "supabase-backend-worker",
    }


@router.get("/avatar-render")
async def get_avatar_render_docs() -> dict[str, object]:
    return {"name": "VideoSpark Avatar Render API", "status": "disabled", "detail": _avatar_disabled_message()}


@router.post("/render", response_model=RenderSuccessResponse)
async def create_render(
    payload: RenderRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> RenderSuccessResponse:
    validate_launch_config(payload)
    payload = apply_launch_defaults(payload)
    credits = calculate_credits(payload)
    job = await create_render_job(user, payload, credits)
    return RenderSuccessResponse(
        pid=job["project_id"],
        workflow=payload.workflow.value,
        webhookUrl=payload.webhook_url,
    )


@router.post("/avatar-render", response_model=RenderSuccessResponse)
async def create_avatar_render(
    payload: AvatarRenderRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> RenderSuccessResponse:
    _ = payload
    _ = user
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_avatar_disabled_message(),
    )


@router.post("/calculate-credits", response_model=CreditEstimateResponse)
async def estimate_credits(
    payload: RenderRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user_or_api_key)],
) -> CreditEstimateResponse:
    validate_launch_config(payload)
    payload = apply_launch_defaults(payload)
    duration = (
        payload.source.duration_seconds
        or payload.options.prompt_target_duration
        or 30
    )
    return CreditEstimateResponse(
        credits=calculate_credits(payload),
        workflow=payload.workflow.value,
        estimated_duration_seconds=float(duration),
    )


def _avatar_disabled_message() -> str:
    return "avatar-render is disabled for the MVP because the current Gemini API path does not support the required avatar/reference-image workflow."

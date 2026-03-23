from __future__ import annotations

from fastapi import HTTPException, status


class VideoSparkError(Exception):
    """Base application error."""


class AuthenticationError(VideoSparkError):
    """Raised when a request cannot be authenticated."""


class AuthorizationError(VideoSparkError):
    """Raised when an authenticated user lacks permission."""


class InsufficientCreditsError(VideoSparkError):
    """Raised when a tenant lacks enough credits."""


class PipelineStepError(VideoSparkError):
    """Raised when a pipeline stage fails."""


class ExternalServiceError(VideoSparkError):
    """Raised when an upstream provider fails."""


def as_http_exception(exc: VideoSparkError) -> HTTPException:
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if isinstance(exc, AuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, InsufficientCreditsError):
        return HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc))
    if isinstance(exc, PipelineStepError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

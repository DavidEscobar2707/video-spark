from __future__ import annotations

import asyncio
import structlog

from app.config import ensure_runtime_settings
from app.tasks.pipeline import process_next_job

logger = structlog.get_logger()


async def run_worker() -> None:
    settings = ensure_runtime_settings()
    logger.info("worker.starting", worker_id=settings.worker_id)
    while True:
        try:
            handled_job = await process_next_job()
        except Exception as exc:
            logger.exception("worker.loop_failed", error=str(exc))
            handled_job = False
        if not handled_job:
            await asyncio.sleep(settings.worker_poll_interval_seconds)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

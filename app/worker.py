import asyncio
import logging

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Job, JobStatus
from app.providers import build_provider
from app.queue import RedisQueue, redis_client

logger = logging.getLogger(__name__)


async def process_job(job_id: str, queue: RedisQueue) -> None:
    settings = get_settings()
    provider = build_provider(settings)
    async with SessionLocal() as session:
        job = await session.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if not job or job.status in {JobStatus.succeeded, JobStatus.dead_letter}:
            return
        job.status = JobStatus.running
        job.attempts += 1
        await session.commit()
        try:
            generation = await provider.generate(job.prompt, job.model)
            job.result = generation.text
            job.prompt_tokens = generation.prompt_tokens
            job.completion_tokens = generation.completion_tokens
            job.estimated_cost_usd = generation.estimated_cost_usd
            job.error = None
            job.status = JobStatus.succeeded
            await session.commit()
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            job.error = str(exc)[:2000]
            if job.attempts >= settings.worker_max_retries:
                job.status = JobStatus.dead_letter
                await session.commit()
                await queue.dead_letter(job.id, job.error)
            else:
                job.status = JobStatus.queued
                await session.commit()
                await asyncio.sleep(settings.worker_retry_base_seconds * (2 ** (job.attempts - 1)))
                await queue.enqueue(job.id)


async def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    redis = redis_client(settings.redis_url)
    queue = RedisQueue(redis)
    logger.info("AgentCloud worker started")
    try:
        while True:
            job_id = await queue.dequeue()
            if job_id:
                await process_job(job_id, queue)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())


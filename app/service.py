from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job
from app.queue import Queue
from app.schemas import JobCreate
from app.telemetry import current_trace_id


async def create_job(
    session: AsyncSession,
    queue: Queue,
    client_id: str,
    idempotency_key: str,
    payload: JobCreate,
    default_model: str,
) -> tuple[Job, bool]:
    existing = await session.scalar(
        select(Job).where(
            Job.client_id == client_id,
            Job.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing, False
    job = Job(
        client_id=client_id,
        idempotency_key=idempotency_key,
        prompt=payload.prompt,
        model=payload.model or default_model,
        trace_id=current_trace_id(),
    )
    session.add(job)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(Job).where(
                Job.client_id == client_id,
                Job.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing, False
        raise
    await session.refresh(job)
    await queue.enqueue(job.id)
    return job, True


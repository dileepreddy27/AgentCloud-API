from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import worker
from app.db import Base
from app.models import Job, JobStatus
from app.providers import Generation


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[str] = []
        self.dead_letters: list[tuple[str, str]] = []

    async def enqueue(self, job_id: str) -> None:
        self.enqueued.append(job_id)

    async def dead_letter(self, job_id: str, error: str) -> None:
        self.dead_letters.append((job_id, error))


class SuccessfulProvider:
    async def generate(self, prompt: str, model: str) -> Generation:
        return Generation("done", 3, 1, 0.001)


class FailingProvider:
    async def generate(self, prompt: str, model: str) -> Generation:
        raise RuntimeError("provider unavailable")


async def make_job(session_maker) -> str:
    async with session_maker() as session:
        job = Job(
            client_id="test-client",
            idempotency_key="worker-test-key",
            prompt="run",
            model="mock-v1",
        )
        session.add(job)
        await session.commit()
        return job.id


@pytest.fixture
async def worker_database(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'worker.db'}")
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(worker, "SessionLocal", session_maker)
    yield session_maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_persists_generation(worker_database, monkeypatch):
    job_id = await make_job(worker_database)
    queue = FakeQueue()
    monkeypatch.setattr(worker, "build_provider", lambda settings: SuccessfulProvider())
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(worker_max_retries=3, worker_retry_base_seconds=0),
    )
    await worker.process_job(job_id, queue)
    async with worker_database() as session:
        job = await session.get(Job, job_id)
        assert job.status == JobStatus.succeeded
        assert job.result == "done"
        assert job.prompt_tokens == 3
        assert job.estimated_cost_usd == 0.001


@pytest.mark.asyncio
async def test_worker_dead_letters_terminal_failure(worker_database, monkeypatch):
    job_id = await make_job(worker_database)
    queue = FakeQueue()
    monkeypatch.setattr(worker, "build_provider", lambda settings: FailingProvider())
    monkeypatch.setattr(
        worker,
        "get_settings",
        lambda: SimpleNamespace(worker_max_retries=1, worker_retry_base_seconds=0),
    )
    await worker.process_job(job_id, queue)
    async with worker_database() as session:
        job = await session.get(Job, job_id)
        assert job.status == JobStatus.dead_letter
        assert job.attempts == 1
        assert "provider unavailable" in job.error
    assert queue.dead_letters == [(job_id, "provider unavailable")]

from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.db import Base, get_session
from app.main import app, settings_dep
from app.rate_limit import RedisRateLimiter


class MemoryQueue:
    def __init__(self) -> None:
        self.items: list[str] = []

    async def enqueue(self, job_id: str) -> None:
        self.items.append(job_id)


@pytest.fixture
async def test_context(tmp_path) -> AsyncIterator[tuple[AsyncClient, MemoryQueue]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def session_override():
        async with session_maker() as session:
            yield session

    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        api_keys={"test-client": "test-secret"},
        rate_limit_requests=2,
    )
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = MemoryQueue()
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[settings_dep] = lambda: settings
    app.dependency_overrides[get_settings] = lambda: settings
    app.state.settings = settings
    app.state.redis = redis
    app.state.queue = queue
    app.state.rate_limiter = RedisRateLimiter(redis, 2, 60)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, queue
    app.dependency_overrides.clear()
    await redis.aclose()
    await engine.dispose()

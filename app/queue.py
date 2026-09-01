import json
from typing import Protocol

from redis.asyncio import Redis

QUEUE_NAME = "agentcloud:jobs"
DEAD_LETTER_QUEUE = "agentcloud:dead-letter"


class Queue(Protocol):
    async def enqueue(self, job_id: str) -> None: ...


class RedisQueue:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def enqueue(self, job_id: str) -> None:
        await self.redis.lpush(QUEUE_NAME, json.dumps({"job_id": job_id}))

    async def dequeue(self, wait_seconds: int = 5) -> str | None:
        item = await self.redis.brpop(QUEUE_NAME, timeout=wait_seconds)
        if not item:
            return None
        return json.loads(item[1])["job_id"]

    async def dead_letter(self, job_id: str, error: str) -> None:
        await self.redis.lpush(DEAD_LETTER_QUEUE, json.dumps({"job_id": job_id, "error": error}))


def redis_client(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)

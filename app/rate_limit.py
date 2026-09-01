from fastapi import HTTPException, status
from redis.asyncio import Redis


class RedisRateLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    async def check(self, client_id: str) -> None:
        key = f"agentcloud:rate:{client_id}"
        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            # NX anchors the window to the first accepted request instead of
            # resetting it on every request or relying on wall-clock buckets.
            pipeline.expire(key, self.window_seconds, nx=True)
            count, _ = await pipeline.execute()
        if int(count) > self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(self.window_seconds)},
            )

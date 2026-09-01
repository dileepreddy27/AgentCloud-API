from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Job
from app.queue import RedisQueue, redis_client
from app.rate_limit import RedisRateLimiter
from app.schemas import HealthResponse, JobCreate, JobRead
from app.security import authenticate_client
from app.service import create_job
from app.telemetry import configure_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.redis = redis_client(settings.redis_url)
    app.state.queue = RedisQueue(app.state.redis)
    app.state.rate_limiter = RedisRateLimiter(
        app.state.redis, settings.rate_limit_requests, settings.rate_limit_window_seconds
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title="AgentCloud API",
    version="0.1.0",
    description="Authenticated asynchronous AI generation jobs with idempotency and accounting.",
    lifespan=lifespan,
)
configure_telemetry(app, get_settings())

Session = Annotated[AsyncSession, Depends(get_session)]
Client = Annotated[str, Depends(authenticate_client)]


def settings_dep() -> Settings:
    return get_settings()


def redis_dep() -> Redis:
    return app.state.redis


@app.get("/health/live", response_model=HealthResponse, tags=["operations"])
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse, tags=["operations"])
async def ready(session: Session, redis: Annotated[Redis, Depends(redis_dep)]) -> HealthResponse:
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "failed"
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "failed"
    if "failed" in checks.values():
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return HealthResponse(status="ok", checks=checks)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/v1/jobs",
    response_model=JobRead,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
    responses={409: {"description": "Idempotency key reused with a different payload"}},
)
async def submit_job(
    payload: JobCreate,
    response: Response,
    session: Session,
    client_id: Client,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    settings: Annotated[Settings, Depends(settings_dep)],
) -> Job:
    await app.state.rate_limiter.check(client_id)
    job, created = await create_job(
        session, app.state.queue, client_id, idempotency_key, payload, settings.llm_model
    )
    payload_mismatch = job.prompt != payload.prompt or job.model != (
        payload.model or settings.llm_model
    )
    if not created and payload_mismatch:
        raise HTTPException(status_code=409, detail="Idempotency key payload mismatch")
    response.status_code = status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
    return job


@app.get("/v1/jobs/{job_id}", response_model=JobRead, tags=["jobs"])
async def get_job(job_id: str, session: Session, client_id: Client) -> Job:
    job = await session.scalar(select(Job).where(Job.id == job_id, Job.client_id == client_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

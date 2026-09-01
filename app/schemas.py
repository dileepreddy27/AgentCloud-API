from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import JobStatus


class JobCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000, examples=["Summarize queue semantics."])
    model: str | None = Field(default=None, max_length=100, examples=["mock-v1"])


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    model: str
    result: str | None
    error: str | None
    attempts: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    trace_id: str | None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)

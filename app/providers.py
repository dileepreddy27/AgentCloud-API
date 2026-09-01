from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings


@dataclass(slots=True)
class Generation:
    text: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float


class LLMProvider(Protocol):
    async def generate(self, prompt: str, model: str) -> Generation: ...


class MockProvider:
    async def generate(self, prompt: str, model: str) -> Generation:
        prompt_tokens = max(1, len(prompt.split()))
        text = f"Mock response ({model}): {prompt.strip()}"
        return Generation(text, prompt_tokens, max(1, len(text.split())), 0.0)


class OpenAICompatibleProvider:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, model: str) -> Generation:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
        body = response.json()
        usage = body.get("usage", {})
        return Generation(
            text=body["choices"][0]["message"]["content"],
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            estimated_cost_usd=0.0,
        )


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockProvider()
    if settings.llm_provider == "openai-compatible":
        if not settings.llm_api_key or not settings.llm_base_url:
            raise RuntimeError("LLM_API_KEY and LLM_BASE_URL are required")
        return OpenAICompatibleProvider(settings.llm_api_key, settings.llm_base_url)
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")


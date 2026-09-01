import pytest

from app.providers import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic():
    provider = MockProvider()
    first = await provider.generate("hello world", "mock-v1")
    second = await provider.generate("hello world", "mock-v1")
    assert first == second
    assert first.prompt_tokens == 2
    assert first.estimated_cost_usd == 0


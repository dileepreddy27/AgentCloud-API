import asyncio
import os

import httpx
import pytest


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("RUN_STACK_TESTS"), reason="set RUN_STACK_TESTS=1 with Compose running"
)
def test_full_async_job_flow():
    async def scenario():
        base_url = os.getenv("AGENTCLOUD_BASE_URL", "http://localhost:18000")
        async with httpx.AsyncClient(base_url=base_url, timeout=20) as client:
            headers = {
                "X-API-Key": "change-me-before-production",
                "Idempotency-Key": "e2e-stack-0001",
            }
            created = await client.post("/v1/jobs", headers=headers, json={"prompt": "integration"})
            assert created.status_code in {200, 202}
            job_id = created.json()["id"]
            for _ in range(40):
                result = await client.get(
                    f"/v1/jobs/{job_id}", headers={"X-API-Key": headers["X-API-Key"]}
                )
                if result.json()["status"] == "succeeded":
                    assert result.json()["result"].startswith("Mock response")
                    return
                await asyncio.sleep(0.25)
            raise AssertionError("job did not complete")

    asyncio.run(scenario())

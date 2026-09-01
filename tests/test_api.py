import pytest


@pytest.mark.asyncio
async def test_requires_authentication(test_context):
    client, _ = test_context
    response = await client.get("/v1/jobs/unknown")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_and_idempotent_replay(test_context):
    client, queue = test_context
    headers = {"X-API-Key": "test-secret", "Idempotency-Key": "request-0001"}
    first = await client.post("/v1/jobs", headers=headers, json={"prompt": "hello"})
    second = await client.post("/v1/jobs", headers=headers, json={"prompt": "hello"})
    assert first.status_code == 202
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(queue.items) == 1


@pytest.mark.asyncio
async def test_idempotency_payload_conflict(test_context):
    client, _ = test_context
    headers = {"X-API-Key": "test-secret", "Idempotency-Key": "request-0002"}
    created = await client.post("/v1/jobs", headers=headers, json={"prompt": "one"})
    assert created.status_code == 202
    response = await client.post("/v1/jobs", headers=headers, json={"prompt": "two"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_job_is_tenant_scoped(test_context):
    client, _ = test_context
    headers = {"X-API-Key": "test-secret", "Idempotency-Key": "request-0003"}
    created = await client.post("/v1/jobs", headers=headers, json={"prompt": "hello"})
    response = await client.get(f"/v1/jobs/{created.json()['id']}", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit(test_context):
    client, _ = test_context
    headers = {"X-API-Key": "test-secret"}
    for i in range(2):
        response = await client.post(
            "/v1/jobs",
            headers={**headers, "Idempotency-Key": f"request-rate-{i}"},
            json={"prompt": "hello"},
        )
        assert response.status_code == 202
    response = await client.post(
        "/v1/jobs",
        headers={**headers, "Idempotency-Key": "request-rate-final"},
        json={"prompt": "hello"},
    )
    assert response.status_code == 429

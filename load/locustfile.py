import uuid

from locust import HttpUser, between, task


class AgentCloudUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def submit_job(self):
        self.client.post(
            "/v1/jobs",
            headers={
                "X-API-Key": "change-me-before-production",
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json={"prompt": "Deterministic load-test prompt"},
        )

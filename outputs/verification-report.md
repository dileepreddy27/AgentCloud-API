# AgentCloud API local verification report

Date: 2026-09-01  
Environment: Windows host, Python 3.11.9, Docker Desktop, deterministic `mock-v1` provider

## Verified

| Claim | Evidence |
|---|---|
| Python source compiles | `python -m compileall -q app` exited successfully. |
| Static checks pass | Ruff reported `All checks passed!`. |
| Automated local suite passes | 8 tests passed; 1 Compose-gated test skipped in the isolated run; measured application coverage 73%. |
| PostgreSQL migration works | Alembic migration container exited 0 against PostgreSQL 16. |
| Redis and PostgreSQL readiness works | `/health/ready` returned `database=ok` and `redis=ok`. |
| Asynchronous end-to-end flow works | Compose-gated test passed through HTTP submission, PostgreSQL, Redis, worker, mock provider, and polling. |
| Idempotency and authentication work | Tests cover missing/invalid authentication, one enqueue per replay, payload-conflict 409, and tenant-scoped access. |
| Rate limiting works | Redis limiter test returns 429 after the configured per-client request count; the window is anchored to the first request rather than a wall-clock bucket. The regression test passed 20 consecutive reruns after the boundary defect was corrected. |
| Accounting works | Worker test verifies persisted prompt tokens and estimated cost fields. |
| Retry terminal/dead-letter behavior works | Worker failure test verifies attempt increment, terminal state, error persistence, and dead-letter publication. |
| Container build/start works | API, worker, PostgreSQL, and Redis containers ran; migration completed successfully. |
| Worker drains submitted jobs | After the sample, Redis queue depth was 0 and PostgreSQL contained 79 succeeded jobs. |
| Short local load sample completed | Locust: 5 users, spawn rate 1/s, configured 15 seconds, temporary 1,000-request limit; 78 requests, 0 failures, 10.19 req/s, 71 ms average, 61 ms median, approximately 530 ms p99/max. |
| Basic secret-pattern scan is clean | Repository scan excluding `.env`, `.venv`, and outputs found no AWS key, private-key header, or obvious quoted long secret pattern. |

The load result describes only this local run. It is not evidence of cloud capacity, sustained throughput,
availability, or production latency. The default request limit was restored to 60 after the sample.

## Configured but not independently verified

| Claim | Status |
|---|---|
| GitHub Actions CI | Workflow is present, but it has not run on GitHub. |
| OTLP trace export | Instrumentation and endpoint configuration are present; no collector/export backend was connected. |
| OpenAI-compatible live provider | Adapter is implemented; no provider credential or billable call was used. |
| AWS ECS/Fargate architecture | Deployment mapping and runbook are documented; no AWS resource was provisioned. |
| Production autoscaling/recovery | Design guidance exists; no multi-node, failover, restore, or chaos exercise was run. |

## Not run / deliberately out of scope

| Item | Reason |
|---|---|
| Paid cloud deployment | Explicitly prohibited without authorization. |
| Remote repository creation or GitHub push | Explicitly prohibited without authorization. |
| Sustained/stress/soak test | A short local sample avoids implying production capacity. |
| Security penetration test and dependency CVE audit | Not performed; the regex scan is not a substitute. |
| Real LLM billing/cost reconciliation | Mock mode is deterministic and zero cost. |

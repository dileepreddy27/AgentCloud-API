# AgentCloud API

AgentCloud API is a portfolio-grade backend demonstrating how an AI request becomes an authenticated,
idempotent asynchronous job rather than a fragile long-running HTTP call. It combines FastAPI,
PostgreSQL, a Redis-compatible queue, separate workers, provider adapters, retries/dead-letter handling,
usage accounting, rate limiting, telemetry hooks, containers, migrations, CI, and an AWS-oriented
operating model.

It is a demonstrable reference implementation—not a claim of production certification or a deployed
cloud system.

## Quick start

```powershell
Copy-Item .env.example .env
# Change API_KEYS in .env before use.
docker compose up --build -d
curl.exe http://localhost:18000/health/ready
```

Submit and poll a job:

```powershell
$headers = @{ "X-API-Key" = "change-me-before-production"; "Idempotency-Key" = "demo-request-0001" }
$job = Invoke-RestMethod -Method Post -Uri http://localhost:18000/v1/jobs -Headers $headers -ContentType application/json -Body '{"prompt":"Explain idempotency in one sentence."}'
Invoke-RestMethod -Uri "http://localhost:18000/v1/jobs/$($job.id)" -Headers @{ "X-API-Key" = "change-me-before-production" }
```

OpenAPI is available locally at `/docs` and `/openapi.json`. The request schema includes examples.

## Engineering highlights

- Database-enforced tenant/idempotency uniqueness and conflict detection.
- Separate API and worker processes with deterministic zero-cost mock inference.
- Exponential retry, terminal dead-letter state, usage tokens, and cost fields.
- Redis-backed distributed per-client request window and tenant-scoped job retrieval.
- Liveness/readiness, Prometheus endpoint, trace IDs, and optional OTLP export.
- Alembic migration, non-root read-only containers, Compose, and GitHub Actions CI.

See the [architecture](docs/architecture.md), [operations runbook](docs/runbook.md),
[security limitations](docs/security.md), and [AWS blueprint](docs/aws-deployment.md).

## Development verification

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

With Compose running, set `RUN_STACK_TESTS=1` and execute the integration test. The
reproducible short Locust scenario is:

```powershell
.\.venv\Scripts\locust.exe -f load/locustfile.py --headless -u 5 -r 1 -t 15s --host http://localhost:18000 --only-summary
```

## Verified local snapshot

On 2026-09-01, the following checks completed locally:

- Ruff passed with no findings.
- The isolated suite passed 8 tests with 1 Compose-gated skip and 73% measured
  application coverage.
- The Compose-gated end-to-end test passed against PostgreSQL 16 and Redis 7,
  covering HTTP submission, queueing, worker execution, persistence, and polling.
- The migration exited successfully, the API reported healthy, and the worker
  drained the Redis queue to zero.
- A short localhost Locust run used 5 users, a 1 user/second spawn rate, a configured
  15-second duration, and a temporary 1,000-request rate limit. It completed 78
  submissions with zero failures at 10.19 requests/second, 71 ms average, 61 ms
  median, and approximately 530 ms p99/max. The default limit was restored afterward.

These results describe one local run only; they do not establish production or cloud
capacity. See the [full verification report](outputs/verification-report.md) for the
verified, configured-but-unverified, and deliberately not-run evidence table.

Cloud deployment, autoscaling, resilience, OTLP export, live-provider behavior, and
provider billing remain unverified.

## Evidence status

The dated report is retained as execution evidence rather than a permanent guarantee. Re-run
the documented commands after meaningful code or environment changes.

# Operations runbook

## Start and validate locally

1. Copy `.env.example` to `.env` and change the development API key.
2. Run `docker compose up --build -d`.
3. Check `GET /health/live`, then `GET /health/ready`.
4. Submit a job on local port `18000` with `X-API-Key` and a unique
   `Idempotency-Key`; poll the returned job ID.

## Signals

- Liveness proves the HTTP process responds; readiness checks PostgreSQL and Redis.
- `/metrics` exposes Prometheus process/runtime metrics. Production should restrict it.
- JSON/structured log aggregation is a planned hardening item; current logs are standard output.
- Set `OTEL_EXPORTER_OTLP_ENDPOINT` to enable OTLP HTTP trace export.

## Common incidents

**Jobs remain queued:** verify worker task count and logs, Redis connectivity, and queue length
(`LLEN agentcloud:jobs`). Scale workers only after checking provider quotas.

**Dead-letter growth:** inspect `agentcloud:dead-letter`, correlate job/trace IDs, remediate the
provider or payload fault, then replay deliberately. This version has no administrative replay API.

**Database unavailable:** readiness removes unhealthy API tasks from traffic. Confirm RDS events,
connections, credentials, and security groups before failover or restore operations.

**Rate-limit errors:** validate whether one API key is shared unexpectedly. Tune limits based on
measured capacity, provider quotas, and tenant policy—not merely client demand.

## Deployment and rollback outline

Run migrations as a one-off ECS task before shifting traffic. Deploy immutable image digests with
a rolling or blue/green strategy. Keep migrations backward-compatible. Roll back the task definition
first; use database downgrade only after a reviewed backup/restore decision.

## Backup and recovery

Enable automated RDS backups and deletion protection. Test point-in-time restore in a non-production
account. Redis is not the system of record; reconstruct queue state from database jobs when necessary.

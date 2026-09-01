# Security and limitations

Implemented controls include constant-time API-key comparison, tenant-scoped reads, input length
limits, database idempotency uniqueness, non-root/read-only containers, secret-free examples,
rate limiting, and dependency-locked major version ranges.

Known limitations:

- API keys are static shared secrets; production should store hashes and use OAuth2/JWT or signed
  workload identities with rotation, revocation, scopes, and audit trails.
- Rate limiting uses a Redis-backed window anchored to each client's first request;
  it is intentionally simpler than a token bucket and does not support weighted costs.
- The Redis queue has no lease/visibility timeout; worker termination after dequeue can strand a job.
- Database commit and enqueue are not atomic; use an outbox/relay or managed durable queue.
- Prompt content and model output are stored unencrypted at the application layer. Apply retention,
  redaction, data classification, and provider privacy policies.
- Cost is zero in mock mode and not priced by the generic provider adapter. Production pricing must
  be versioned by provider/model and reconciled against invoices.
- `/metrics` and API docs require network-level restriction in production.
- No content moderation, prompt-injection defense, malware scanning, customer-managed encryption,
  administrative replay endpoint, or formal compliance claim is included.

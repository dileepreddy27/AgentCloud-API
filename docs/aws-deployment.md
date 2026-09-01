# AWS deployment blueprint (not executed)

This is documentation, not provisioned infrastructure. Use separate accounts/environments and an
IaC tool such as Terraform or AWS CDK. Build once, scan, sign if required, and promote an immutable
ECR digest.

Create private subnets across at least two availability zones; expose only an ALB. Run API and worker
as separate ECS/Fargate services. Permit ALB-to-API, task-to-RDS, task-to-ElastiCache, and controlled
egress only. Store configuration in SSM Parameter Store and secrets in Secrets Manager. Run Alembic
as a one-off deployment task. Autoscale API on request/latency signals and workers on queue age/depth.

Required production decisions include SQS versus Redis queueing, regional recovery objectives,
tenant authentication, provider egress controls, PII retention, budgets/alarms, WAF policy, log
redaction, image signing, and database connection sizing.


Messaging Runbook

Day-1: Bootstrap
- Start stack: `docker compose -f configs/messaging/docker-compose.dev.yml up -d`
- Bootstrap tenants: `./tools/messaging/bootstrap.sh --tenants main`
- Verify topics in Console and NATS varz.
- Generate ACLs if needed: `./tools/messaging/gen-acl.sh main`

Day-2: Operate
- Scale partitions: adjust topic partitions per hot tenants/models.
- Manage ACLs: rotate credentials and reapply ACL JSON.
- Monitor lag/throughput via metrics and Grafana dashboard.
- Handle DLQ: inspect `llm.<tenant>.dlq.*`; replay via retry topics.

Failure Scenarios
- Schema errors: rollback schema version; ensure compatibility mode is backward.
- Consumer failures: dedupe by key; use retry with exponential backoff.
- Backpressure: auto-scale workers based on lag threshold.

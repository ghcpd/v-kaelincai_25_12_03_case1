Collection Checklist for Legacy issue_project

Missing data and assumptions (high level):

- Production logs (last 30 days) for scheduler/routing service
- Full DB schema and snapshots for appointment/state tables
- Traffic traces (sample request IDs and payloads) across peak hours
- Auth and API keys, secrets, and OAuth flow details
- Deployment manifests (k8s, docker-compose, cloud infra) and env variables
- Monitoring dashboard metrics and alert rules (latency, error rate)
- Runtime configuration and feature flags
- Expected SLAs and SLOs (p99 latency, availability)
- Third-party API contracts (calendar, notification, payment)
- Any existing canary or A/B rollout strategy

Checklist items to collect and share:

- Codebase
  - Complete repository (branches) and README, CI pipelines
  - Known failing tests and historical commits where behavior changed
- Logs
  - Application logs, stack traces, request/response payloads, correlation IDs
  - System logs for infra (load balancers, proxies)
- DB snapshots
  - Schema DDL and representative data subset
  - Migration history and data retention policy
- Traffic
  - Sample requests for all endpoints (normal and edge cases)
  - Traffic volume metrics and peak load periods
- Monitoring & Alerts
  - Dashboards and alert thresholds
  - Recent incidents and postmortems
- Security/Access
  - Vault or secrets configuration, RBAC policies, audit logs
- Tests & Fixtures
  - Test harness, integration tests, mocks, demo environment

How to produce missing artifacts (quick wins):

- Enable structured logging and capture a 1-hour trace in staging with a request-id header
- Export DB snapshot with anonymized PII and include migration history
- Create a replayable traffic capture (bursts and steady-state) for 1 day
- Export current CI pipeline logs and failing test outputs

Next step: background reconstruction from repository assets and failing tests.
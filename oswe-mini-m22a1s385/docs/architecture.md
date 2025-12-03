Greenfield Replacement Architecture (Appointment Scheduling)

Objective:
Design a resilient, observable, and testable appointment scheduling service (v2) that replaces the legacy routing library with a service-oriented architecture supporting idempotency, retries with backoff, circuit breakers, transactional outbox or Saga compensation, and clear migration paths.

Service decomposition (high level):
- API Gateway / Edge: Authentication, rate limiting, TLS termination, request-id propagation.
- Appointment API Service (stateless): Accepts appointment create/update/cancel, validates input, enqueues command to Scheduling Engine, applies idempotency key checks, returns immediate acknowledgment.
- Scheduling Engine (stateful): Contains scheduling algorithms (graph-based, constraints); runs background reconciliation and conflict resolution; exposes a query API.
- Worker / Executor (async): Executes tasks (notify users, persist to DB), reads from work-queue; uses transactional outbox pattern to publish domain events.
- Event Bus (Kafka / RabbitMQ): Durable event streaming for inter-service integration and audit.
- Persistence: Postgres for canonical state, Redis for caching, and an object store for snapshots/backups.
- Observability & Control Plane: Prometheus metrics, Grafana dashboards, structured logs (JSON), Sentry for errors.

ASCII Architecture

Client -> API Gateway -> Appointment API -> Scheduling Engine -> DB
                                 |                     |
                                 v                     v
                              Worker -> Outbox -> Event Bus -> Notifications

Key design choices:

- Unified state machine: Appointment state transitions: INIT -> SCHEDULED -> CONFIRMED -> IN_PROGRESS -> COMPLETED | CANCELLED | FAILED
- Idempotency: Every client command must include an idempotency_key. The Appointment API stores idempotency keys in DB and returns current result if duplicate.
- Retry & backoff: Use exponential backoff with jitter for transient errors (max attempts configurable). Workers use retry counts in event metadata.
- Circuit breaker & timeouts: For third-party integrations (calendar APIs, notifications) use circuit breakers (e.g., Hystrix/Resilience4j patterns), with short timeouts to avoid thread exhaustion.
- Compensation & SAGA: For distributed transactions, use a Saga orchestrator or choreography. Example: create appointment -> reserve slot in calendar (external) -> persist booking. On failure, compensate by releasing reservation and sending user notifications.
- Transactional Outbox: Use DB transactional outbox pattern to guarantee event publication aligned with state changes; Outbox consumer publishes to Event Bus.

API Schema (Appointment Create) — JSON

POST /v1/appointments
{
  "idempotency_key": "uuid-v4",       // required
  "customer_id": "uuid-v4",          // required
  "slot": {
    "start_time": "2025-12-03T10:00:00Z", // ISO8601 UTC
    "end_time": "2025-12-03T10:30:00Z"
  },
  "location": "string",              // optional, max 255
  "service_type": "enum: [consultation, pickup]", // required
  "metadata": { }                      // optional freeform JSON
}

Field constraints and validation
- idempotency_key: 36-char UUID v4 or base64, must be unique for client request window (24h)
- customer_id: valid UUID
- slot.start_time < slot.end_time; duration <= 4 hours
- service_type: must be one of allowed enums
- metadata: size <= 8KB

State Machine and Crash Points
- Transitions executed atomically in DB via state and version columns (optimistic concurrency)
- Crash points: after DB write but before outbox publish; during external API call; during worker processing
- In each crash, worker uses idempotency and outbox to reconcile state and retry or run compensation.

Migration & Parallel Run

Approaches:
- Shadow routing: Deploy v2 alongside v1; replicate traffic (read/write) in shadow mode to validate behavior.
- Dual-write/dual-read: API writes to both v1 and v2 during a canary period; backfill v2 from v1 snapshot for historical data.
- Cutover: Use feature flag to slowly route traffic to v2; maintain a rollback plan (drain queues, pause writes to v2)

Backfill & Rollback:
- Backfill: Bulk export from legacy DB -> transform -> load into v2 DB. Use idempotent import jobs with checkpoints.
- Rollback: Stop writes to v2, drain outbox, and switch traffic back to v1. Keep v2 in read-only for forensics.

Next step: define integration tests focused on crash points, idempotency, retry/backoff, and reconciliation.
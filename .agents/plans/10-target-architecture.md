# Target Architecture

Reviewed: 2026-08-25
Status: accepted
Role: target baseline
Depends on: `00-source-assessment.md`

## 1. Shape

Target is a modular Django monolith with multiple explicit processes:

```text
Authenticated Django admin      MQTT/Rabbit ingress      Scheduler
            |                           |                    |
            +------------- adapters / command handlers -----+
                                        |
                              application services
                                        |
                               pure domain policies
                                        |
             +--------------------------+--------------------------+
             |                          |                          |
        repositories              game-event append          outbox append
             |                          |                          |
             +--------------------- PostgreSQL --------------------+
                                                                    |
                                                         outbox publisher
                                                                    |
                                                               RabbitMQ
                                                +-------------------+------------------+
                                                |                   |                  |
                                          device delivery      feed projection   operator projection
                                                |                   |                  |
                                               MQTT            PostgreSQL/cache   Django admin
```

PostgreSQL owns committed state and durable session history. RabbitMQ owns asynchronous delivery. MQTT remains physical-device transport.

## 2. Runtime Processes

| Process | Responsibility | Must not own |
| --- | --- | --- |
| `web_admin` | authenticated operator configuration/control, media/static integration, read models | transport routing or hidden model side effects |
| `mqtt_ingress` | validate routing/payload, maintain transport-local keepalive, create normalized commands | game decisions |
| `domain_worker` | execute commands through application services | raw MQTT parsing |
| `outbox_publisher` | claim committed outbox rows, publish with confirmation, record outcomes | domain decisions |
| `device_delivery` | build compatible CUP/config packets and publish through MQTT | persistence outside delivery status/reconciliation |
| `state_ingress` | persist supported reported device state through services | desired-state decisions |
| `projection_worker` | build player/operator read models idempotently | authoritative domain mutation |
| `scheduler` | determine due work and enqueue commands | direct domain mutation or device publication |

Processes may share one image and repository. Separate deployment repositories or microservices are not required.

### 2.1 Worker Executable and Process Isolation

- One worker executable may provide shared bootstrap, connection setup, envelope parsing,
  handler registration, and a `--role` selector.
- Each role above remains a separate production process with its own queues, settlement
  policy, concurrency/prefetch settings, health signal, and graceful shutdown boundary.
- An `--role all` mode may co-locate roles for development and tests only. Production
  co-location requires accepted P0 workload evidence plus failure and settlement tests
  showing that shared capacity and restart scope are safe.
- RabbitMQ performs responsibility-level routing into dedicated queues; the worker
  executable must not replace them with one broad catch-all queue.
- Do not create a generic persistence worker for authoritative state. Domain workers own
  state, required audit/domain records, and outbox creation in one transaction; only
  idempotent, rebuildable projections use separate persistence consumers.

## 3. Code Boundaries

Keep existing Django app labels and migrations stable while introducing these layers inside each slice:

```text
server/<domain>/
    models/ or models.py       # ORM schema and local persistence invariants
    dto.py                     # commands, snapshots, results, domain events
    policies.py or services/   # pure rules and application use cases
    repositories.py            # ORM queries and writes
    admin.py                   # operator adapter only
    handlers.py                # worker/transport adapter only
    tests/

server/infrastructure/
    rabbitmq/
    mqtt/
    outbox/
    observability/
```

Exact package relocation may occur late. Layer ownership matters before directory perfection. Avoid creating a generic `app/` that permanently duplicates all existing domain packages.

## 4. Dependency Direction

Allowed:

```text
admin/worker/scheduler adapter
  -> application service
  -> domain policy + DTO
  -> repository/outbox interfaces
  -> Django/Rabbit/MQTT implementations
```

Forbidden:

- Domain policy importing Django request/admin/Kombu/MQTT objects.
- Repository publishing messages or rendering HTTP/admin responses.
- Model `save()` publishing RabbitMQ/MQTT work.
- Serializer/form owning game rules.
- Transport handler directly coordinating unrelated model writes.
- `core` accumulating domain-specific rules.
- Application service depending on DRF or Django Ninja.

## 5. Transaction Boundary

One command execution must establish one explicit database transaction for required effects:

```text
load locked/versioned state
-> decide transition
-> persist new state
-> append immutable GameEvent rows
-> append OutboxMessage rows
-> commit
```

Publication occurs after commit in a separate outbox worker. Optional operational logs must never decide transaction success.

For each service define:

- isolation/locking strategy;
- idempotency key;
- command validation;
- expected domain conflicts;
- committed events;
- downstream commands;
- retry-safe result.

## 6. Admin Boundary

Django admin replaces the abandoned operator API/panel. It must be treated as an adapter, not as the domain layer.

Admin rules:

- Require authenticated staff roles and explicit model/action permissions.
- Route stateful actions through the same application service used by workers.
- Keep history/event projections read-only.
- Do not expose access codes, passwords, secrets, raw payloads, or arbitrary JSON unnecessarily.
- Make destructive/cascade behavior visible before confirmation.
- Record operator actor and correlation ID for control actions.
- Separate read-only diagnostics from repair commands.
- Provide management commands for bulk/import/repair workflows that do not fit safe admin actions.

## 7. Event Categories

| Category | Meaning | Storage/delivery |
| --- | --- | --- |
| Command | request to attempt a change | RabbitMQ queue; idempotent handler |
| Domain event | committed game fact | PostgreSQL `GameEvent` plus outbox |
| Player feed entry | safe presentation derived from events | projection table/cache, terminal delivery |
| Operator event entry | monitoring/investigation projection | read-only Django admin |
| Audit event | privileged operator/security fact | append-only retained record |
| Operational log | software/infrastructure diagnostic | structured logging backend |
| Metric | numeric runtime health signal | monitoring system |

Never reuse one generic table for all categories.

## 8. Compatibility Boundaries

Preserve until explicitly versioned and verified:

- existing Django app labels, migration graph, table names, IDs, and foreign keys;
- `skaben_data.json` configuration compatibility after runtime-state cleanup;
- MQTT routing `<topic>.<uid>.<command>` and inbound `ask.<topic>.<uid>.<command>`;
- PING/PONG/CUP/SUP/INFO roles;
- lock ACL and device configuration payloads;
- alert state ordering, thresholds, counter semantics, and refresh fanout;
- terminal account/menu/content and asset URLs needed by deployed terminals;
- historical `StreamRecord` fields during game-history migration.

## 9. Settings and Bootstrap

Target settings provide explicit, typed values for:

- environment/debug mode;
- secret key;
- allowed hosts and CSRF origins;
- database;
- Redis;
- RabbitMQ/MQTT;
- scheduler and keepalive timeouts;
- static/media paths;
- worker concurrency/prefetch;
- retry/DLQ policy;
- logging/metrics.

Required bootstrap checks:

- settings import;
- Django setup;
- URLConf and WSGI import;
- migrations/check command;
- admin URL;
- every management command import;
- Rabbit topology declaration against integration broker;
- graceful shutdown of consumers and scheduler.

## 10. Non-Goals

- No microservice split during domain migration.
- No Kafka.
- No TimescaleDB without telemetry evidence.
- No replacement SPA/operator panel.
- No generic public API.
- No event-sourced rewrite of all domain state.
- No schema relocation merely for cosmetic package structure.

# Game Events, Session History, and RabbitMQ Plan

Reviewed: 2026-08-25
Status: proposed
Depends on: `20-migration-roadmap.md`, `10-target-architecture.md`, and the history, transport, and worker routes in `../context-routing.yml`

## 1. Objective [P4/P5]

Replace the generic `streams` module with explicit durable game history and projections while using RabbitMQ for reliable internal distribution and MQTT for terminal/device delivery.

The old capability served or intended to serve three product concerns:

1. Player-visible game feed.
2. Complete game-session history.
3. Operator monitoring.

Operational software logs are a fourth, separate concern and must not share the same domain model.

## 2. Ownership [P4/P5]

### P4 foundation ownership

| Component | Responsibility | Storage/transport |
| --- | --- | --- |
| `AuditEvent` | immutable operator/security/control-plane fact; optional session link | PostgreSQL |
| `OutboxMessage` | pending/confirmed/retry/dead publication work | PostgreSQL |
| `ConsumerReceipt` or unique consumer key | command/domain-consumer idempotency | PostgreSQL |
| RabbitMQ | asynchronous command/event delivery foundation | durable exchanges/queues |
| MQTT | compatible physical terminal/device delivery boundary | existing compatible topics |
| Structured logger/metrics | process and infrastructure diagnostics | logging/monitoring backend |

### P5 history ownership

| Component | Responsibility | Storage/transport |
| --- | --- | --- |
| `GameSession` | lifecycle and identity of one game run | PostgreSQL |
| `GameEvent` | immutable canonical fact within a session | PostgreSQL |
| `PlayerFeedEntry` | filtered player-facing projection | PostgreSQL/cache |
| `OperatorEventEntry` | monitoring/investigation projection | PostgreSQL/read-only admin |
| Unique projection key | projection idempotency | PostgreSQL |

RabbitMQ is not permanent session storage. PostgreSQL `GameEvent` is canonical history.

## 3. Command and Game Event Contracts [P4/P5]

### Command envelope [P4]

Minimum envelope:

```json
{
  "command_id": "uuid",
  "command_type": "alert.counter.increase",
  "schema_version": 1,
  "requested_at": "2026-08-25T12:30:00Z",
  "actor": {"type": "device", "id": "uuid"},
  "source": "mqtt",
  "session_id": null,
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "payload": {}
}
```

Rules:

- `command_id`, `command_type`, `schema_version`, `requested_at`, `source`, `correlation_id`, and `payload` are required.
- `actor`, `session_id`, and `causation_id` are optional only when the command type permits absence.
- Retries retain the same `command_id`; command type and payload schemas are versioned.
- Adapters preserve legacy source/device identity while translating into this envelope.

### Game event envelope [P5]

Minimum envelope:

```json
{
  "event_id": "uuid",
  "event_type": "lock.opened",
  "schema_version": 1,
  "session_id": "uuid",
  "sequence": 42,
  "occurred_at": "2026-08-24T12:30:00Z",
  "recorded_at": "2026-08-24T12:30:00Z",
  "actor": {"type": "user", "id": "uuid"},
  "subject": {"type": "lock", "id": "uuid"},
  "source": "lock-device",
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "visibility": "players",
  "payload": {}
}
```

Rules:

- `event_id` globally unique.
- `GameEvent.session_id` is required; `AuditEvent` is separate and may link to a session optionally.
- `(session_id, sequence)` unique and deterministic.
- `occurred_at` is domain occurrence time; `recorded_at` is server commit time.
- Payload schema versioned per event type.
- Actor/subject identifiers remain meaningful after display names change.
- Store safe historical display snapshots only when necessary for durable rendering.
- Events append-only. Corrections use new correction/tombstone events with actor/reason.

Initial event catalog should cover only characterized flows, for example:

- `session.started`, `session.ended`;
- `alert.counter_changed`, `alert.state_changed`;
- `access.granted`, `access.denied`;
- `lock.opened`, `lock.closed`, `lock.blocked`;
- `terminal.authenticated`, `terminal.content_selected` where product-relevant;
- operator control/audit events.

Do not turn every MQTT packet or debug message into a game event.

## 4. Transactional Outbox [P4]

Required domain transaction:

```text
domain state write
-> required AuditEvent or durable domain-record append
-> OutboxMessage append
-> commit
```

P4 does not create `GameSession`, append session-scoped `GameEvent` rows, or build player/operator projections. P5 replaces the durable domain-record step with or augments it by a session-scoped `GameEvent` only when the characterized fact belongs to an active game session.

Outbox fields:

- ID/event ID;
- exchange and routing key;
- headers/envelope/body;
- created/available timestamps;
- attempt count and last error;
- claim/lease owner and expiry;
- confirmed timestamp;
- terminal status (`pending`, `confirmed`, `dead`);
- correlation/session/aggregate metadata for operations.

Publisher requirements:

- prevent two publishers from owning the same pending work concurrently;
- publish persistent messages with broker confirmation and visible unroutable outcomes;
- retain failed work for bounded retry and expose terminal failure;
- recover abandoned work after publisher death.

Detailed claim, lease, retry, retention, and recovery algorithms belong to `P4-W1`, not this cross-phase plan.

## 5. RabbitMQ Topology and Ownership [P4/P5]

Use routing keys RabbitMQ can evaluate. Do not put event type only in headers while binding one broad queue.

### P4 foundation

```text
Exchange: skaben.commands (topic, durable)
  command.alert.*
  command.device.*
  command.terminal.*

Exchange: skaben.events (topic, durable)
  event.alert.*
  event.device.*

Queues:
  skaben.alert.commands
  skaben.device.commands
  skaben.device-delivery.commands
  skaben.<consumer>.retry
  skaben.<consumer>.dead
```

P4 establishes command routing, domain-worker isolation, confirmed outbox publication, retry/DLQ behavior, and compatible device delivery. It does not activate history or projection consumers.

### P5 additions

```text
Exchange: skaben.events (topic, durable)
  event.session.*
  event.access.*
  event.lock.*
  event.terminal.*

Queues:
  skaben.player-feed.events
  skaben.operator-monitor.events
  skaben.<projection>.retry
  skaben.<projection>.dead
```

P5 adds session-history publication and projection consumers only after `P5-W1` defines their durable history and rebuild contracts.

Existing MQTT/internal routing stays compatible during transition. Bridge/adapters may publish both old and new routes temporarily, but dual publication requires an event ID and reconciliation so effects do not duplicate.

Ownership matrix:

| Phase | Source | Exchange / routing key | Queue | Consumer process | Transaction and settlement owner |
| --- | --- | --- | --- | --- | --- |
| P4 | MQTT `INFO` ingress | `skaben.commands` / `command.<domain>.*` | dedicated domain command queue | `mqtt_ingress` then `domain_worker` | ingress owns validated handoff; domain worker owns command transaction and final command settlement |
| P4 | MQTT `SUP` ingress | `skaben.commands` / `command.device.reported_state` | state-ingress command queue | `mqtt_ingress` then `state_ingress` | ingress owns validated handoff; state ingress owns persistence transaction and settlement |
| P4 | Scheduler | `skaben.commands` / `command.<domain>.scheduled` | dedicated domain command queue | `scheduler` then `domain_worker` | scheduler owns enqueue outcome; domain worker owns command transaction and settlement |
| P4 | Django admin | direct application-service call | none | `web_admin` | application service owns transaction; HTTP response follows committed result |
| P4 | Committed domain/audit outbox | `skaben.events` / `event.<domain>.*` | dedicated domain-event queue | `outbox_publisher` then owning domain consumer | publisher owns confirmed delivery status; domain consumer owns its transaction and settlement |
| P4 | Device-refresh outbox | `skaben.commands` / `command.device.refresh_requested` | device-delivery queue | `outbox_publisher` then `device_delivery` | publisher owns confirmed handoff; delivery process owns delivery outcome/reconciliation |
| P5 | Committed `GameEvent` outbox | `skaben.events` / `event.<game-domain>.*` | dedicated player/operator projection queues | `outbox_publisher` then projection workers | publisher owns confirmed delivery status; each projection worker owns its transaction and settlement |

P4 bindings and settlement outcomes are completed in `P4-W1`; P5 projection bindings belong to `P5-W1`. This table fixes responsibility and prevents broad shared-queue ownership.

## 6. Consumer Settlement [P4]

| Outcome | Action |
| --- | --- |
| Valid, committed success | ACK |
| Already processed event/command ID | ACK and record duplicate metric |
| Validation/schema/unsupported version | reject to DLQ; no infinite retry |
| Temporary DB/broker dependency failure | bounded delayed retry |
| Domain conflict | typed policy: ACK rejected result or retry only if conflict is transient |
| Poison message/retry exhausted | DLQ plus operator-visible failure |
| Process death before commit | broker redelivery; idempotency prevents duplicate effect |

Consumers must not ACK in unconditional `finally` blocks.

## 7. Ordering [P5]

Canonical order comes from `(session_id, sequence)` in PostgreSQL, not Rabbit delivery timing.

P5 must preserve per-session canonical order, detect duplicates/gaps, and rebuild projections from PostgreSQL history. Sequence allocation, concurrency, gap recovery, and any later sharding algorithm belong to `P5-W1`.

## 8. Player Feed Projection [P5]

Projection rules:

- Only events explicitly permitted for players.
- Deterministic session order.
- Redact access codes, passwords, internal device IDs, errors, and operator-only metadata.
- Render from structured event fields, not only stored free-form message text.
- Preserve enough name/label snapshot data for historical display.
- Define retention and maximum feed length separately from canonical history.
- Support terminal reconnect through snapshot plus optional delta/cursor.

Delivery options, preferred order:

1. MQTT terminal CUP/feed snapshot or versioned delta.
2. Narrow authenticated read endpoint only if terminal protocol proves HTTP pull is required.

Terminals must not connect directly to RabbitMQ.

## 9. Operator Monitoring Projection [P5]

Expose through read-only Django admin:

- session timeline;
- event type, actor, subject, source, and correlation;
- desired/reported device state where relevant;
- outbox publication and projection status;
- retries, DLQ records, and detected sequence gaps;
- filters by session, time, device, user, lock, severity/category.

Admin must not edit/delete canonical events. Corrections are explicit audited actions producing new events.

Operational monitoring remains separate:

- queue depth, outbox age, consumer lag, retry/DLQ counts as metrics;
- worker crashes and stack traces as structured logs/error tracking;
- device liveness as runtime projection/metric;
- no public generic log CRUD.

## 10. Legacy Stream Migration [P5]

Observed legacy fields to preserve during assessment:

- UUID;
- integer timestamp;
- message and JSON data;
- stream;
- source;
- mark/severity;
- conventional values `game`, `log`, `info`, `error`.

Migration policy:

1. Profile deployed values, volume, duplicates, sensitive data, and actual readers.
2. Export immutable archive before transformation.
3. Separate `game` and `log` records.
4. Map only records with sufficient semantics into `GameEvent`/legacy-history projection.
5. Preserve unmappable records as legacy archive; do not invent session, actor, order, or event type.
6. Route operational logs to logging system rather than `GameEvent`.
7. Keep compatibility read access only until terminal/operator migration is verified.
8. Drop legacy table/module after retention and restore policy is approved.

## 11. Minimum Tests [P4/P5]

### P4 tests

- Domain transaction atomically commits state, required audit/domain record, and outbox; rollback leaves none.
- Publisher confirmation marks the correct row; broker outage retains retryable work.
- Process death or lease expiry causes safe retry; unroutable work becomes visible failure.
- Duplicate command changes state once; retry exhaustion reaches DLQ without an infinite loop.
- Existing severity/header loss is characterized and fixed for new domain/audit records.
- Metrics expose outbox age, publish failure, queue depth, retries, and DLQ count.

### P5 tests

- Session transaction atomically commits state, `GameEvent`, and outbox; rollback leaves none.
- Duplicate event changes each projection once.
- Session sequence remains unique under concurrent events.
- Projection detects a gap and rebuilds from canonical history.
- Player feed redacts operator/security fields; reconnect snapshot/delta has deterministic cursor/order.
- Operator admin is read-only for canonical events.
- Legacy game/log/null/arbitrary payload variants migrate or archive according to policy.
- Metrics expose projection lag.

## 12. Cutover Gates [P4/P5]

P4 owns Rabbit/event-outbox readiness and alert delivery cutover. P5 owns session history, projections, and legacy stream migration. Passing P4 must not imply authorization to implement or cut over P5 work.

### P4 gate

- Event/command schema-version compatibility process documented.
- Outbox and Rabbit failure paths pass integration tests.

### P5 gate

- Game session ownership and lifecycle defined.
- PostgreSQL history can rebuild both projections.
- Real terminal/player feed consumer verified.
- Operator monitoring workflow accepted.
- Legacy stream data archived and migration counts reconciled.
- No required game history depends solely on RabbitMQ retention or process logs.

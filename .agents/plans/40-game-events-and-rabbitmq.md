# Game Events, Session History, and RabbitMQ Plan

Reviewed: 2026-08-24
Status: proposed
Depends on: `server/streams/.agent-review`, `server/core/transport/.agent-review`, `server/core/worker_queue_handlers/.agent-review`, `server/event_contexts/.agent-review`, `10-target-architecture.md`

## 1. Objective

Replace the generic `streams` module with explicit durable game history and projections while using RabbitMQ for reliable internal distribution and MQTT for terminal/device delivery.

The old capability served or intended to serve three product concerns:

1. Player-visible game feed.
2. Complete game-session history.
3. Operator monitoring.

Operational software logs are a fourth, separate concern and must not share the same domain model.

## 2. Ownership

| Component | Responsibility | Storage/transport |
| --- | --- | --- |
| `GameSession` | lifecycle and identity of one game run | PostgreSQL |
| `GameEvent` | immutable canonical fact within a session | PostgreSQL |
| `OutboxMessage` | pending/confirmed/retry/dead publication work | PostgreSQL |
| `PlayerFeedEntry` | filtered player-facing projection | PostgreSQL/cache |
| `OperatorEventEntry` | monitoring/investigation projection | PostgreSQL/read-only admin |
| `ConsumerReceipt` or unique projection key | consumer idempotency | PostgreSQL |
| RabbitMQ | asynchronous command/event delivery | durable exchanges/queues |
| MQTT | physical terminal/device delivery | existing compatible topics |
| Structured logger/metrics | process and infrastructure diagnostics | logging/monitoring backend |

RabbitMQ is not permanent session storage. PostgreSQL `GameEvent` is canonical history.

## 3. Game Event Contract

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

## 4. Transactional Outbox

Required domain transaction:

```text
domain state write
-> GameEvent append
-> OutboxMessage append
-> commit
```

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

Publisher behavior:

1. Claim rows with bounded batch and `select_for_update(skip_locked=True)` or equivalent lease.
2. Publish persistent message with publisher confirms.
3. Use mandatory delivery or alternate exchange for unroutable messages.
4. Mark confirmed only after broker confirmation.
5. On failure, retain row with bounded exponential backoff.
6. Mark terminal failure/dead after policy limit and alert operator.
7. Reclaim expired leases after process death.

## 5. RabbitMQ Topology

Use routing keys RabbitMQ can evaluate. Do not put event type only in headers while binding one broad queue.

Suggested topology:

```text
Exchange: skaben.commands (topic, durable)
  command.alert.*
  command.device.*
  command.terminal.*

Exchange: skaben.events (topic, durable)
  event.session.*
  event.alert.*
  event.access.*
  event.lock.*
  event.terminal.*

Queues:
  skaben.alert.commands
  skaben.device.commands
  skaben.player-feed.events
  skaben.operator-monitor.events
  skaben.device-delivery.commands
  skaben.<consumer>.retry
  skaben.<consumer>.dead
```

Existing MQTT/internal routing stays compatible during transition. Bridge/adapters may publish both old and new routes temporarily, but dual publication requires an event ID and reconciliation so effects do not duplicate.

## 6. Consumer Settlement

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

## 7. Ordering

Canonical order comes from `(session_id, sequence)` in PostgreSQL, not Rabbit delivery timing.

Initial operational choice:

- one consumer per projection queue where volume permits;
- verify incoming sequence and detect gaps;
- idempotently apply duplicate events;
- rebuild projection from PostgreSQL history when gap cannot be reconciled.

If scaling later, shard by stable `hash(session_id)` so one session stays ordered. Do not introduce complex sharding before measured need.

## 8. Player Feed Projection

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

## 9. Operator Monitoring Projection

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

## 10. Legacy Stream Migration

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

## 11. Minimum Tests

- Domain transaction atomically commits state, game event, and outbox.
- Rollback leaves none of the three.
- Publisher confirmation marks correct row only.
- Broker outage retains retryable outbox row.
- Process death/lease expiry causes safe retry.
- Unroutable message becomes visible failure.
- Duplicate event/command changes each projection/state once.
- Retry exhaustion reaches DLQ without infinite loop.
- Session sequence remains unique under concurrent events.
- Projection detects gap and rebuilds from canonical history.
- Player feed redacts operator/security fields.
- Terminal reconnect snapshot/delta has deterministic cursor/order.
- Operator admin is read-only for canonical events.
- Legacy game/log/null/arbitrary payload variants migrate/archive according to policy.
- Existing severity/header loss is characterized and fixed for new events.
- Metrics expose outbox age, publish failure, queue depth, retries, DLQ, and projection lag.

## 12. Cutover Gate

- Game session ownership and lifecycle defined.
- Event schema/version compatibility process documented.
- PostgreSQL history can rebuild both projections.
- Outbox and Rabbit failure paths pass integration tests.
- Real terminal/player feed consumer verified.
- Operator monitoring workflow accepted.
- Legacy stream data archived and migration counts reconciled.
- No required game history depends solely on RabbitMQ retention or process logs.


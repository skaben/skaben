# Alert Migration Pilot

Reviewed: 2026-08-25
Status: proposed
Role: first vertical slice
Depends on: `20-migration-roadmap.md`, `10-target-architecture.md`, and the alert route in `../context-routing.yml`

## 1. Objective

Use alert state/counter behavior as first complete application-service slice. Borrow tested extraction ideas from `refactor_reference/app`, resolved through the source registry in `README.md`, but correct its transaction, queue, settlement, and admin gaps before runtime cutover.

Phase ownership:

- P3 owns DTO/policy/repository extraction, characterization, and non-mutating shadow comparison.
- P4 owns schema constraints, transaction/audit/outbox integration, adapters, settlement, and runtime cutover.

## 2. Source Material to Adapt

Useful prototype files:

- `/home/zerthmonk/skaben_refactor_reference/app/dto/alert.py`
- `/home/zerthmonk/skaben_refactor_reference/app/services/alert_state_machine.py`
- `/home/zerthmonk/skaben_refactor_reference/app/services/alert_auto_change.py`
- `/home/zerthmonk/skaben_refactor_reference/app/repositories/alert.py`
- `/home/zerthmonk/skaben_refactor_reference/app/adapters/internal_alert.py`
- `/home/zerthmonk/skaben_refactor_reference/app/adapters/scheduler_alert.py`
- `/home/zerthmonk/skaben_refactor_reference/app/tests/tests_alert/`

Do not copy prototype MQ publisher, broad alert worker, minimal settings, stream repository, or Compose cutover as-is.

## 3. Target Components

| Component | Responsibility |
| --- | --- |
| `AlertCounterCommand` | typed set/increase/decrease request with source, actor, idempotency, correlation |
| `SetAlertStateCommand` | typed state request with counter-reset policy |
| `AlertStateSnapshot` | immutable current/config state used by policy |
| `AlertPolicy` | pure threshold/state/auto-change decision |
| `AlertTransition` | new counter/state plus domain events and refresh requirements |
| `AlertRepository` | locked/versioned snapshot load and persistence |
| `AlertService` | transaction, policy call, state/audit/domain-record/outbox persistence |
| `AlertAdminAdapter` | validated staff actions calling `AlertService` |
| `AlertCommandHandler` | Rabbit command decoding, service invocation, settlement |
| `AlertSchedulerAdapter` | enqueue due auto-change command, never mutate state directly |

## 4. Preserved Behavior

Characterize from current code/reviews before changes:

- set/increase/decrease counter arithmetic;
- ordered in-game threshold mapping;
- counter snapshot/comment behavior;
- explicit state request and optional counter reset;
- auto-change modes, levels, timeouts, dampening, and boundary behavior;
- current-state uniqueness expectation;
- scale-only refresh after counter changes;
- all-active-topic refresh after state changes;
- required log/game-history messages and source conventions where consumers depend on them;
- scheduler Redis/time-gate behavior until deliberately replaced.

Do not preserve accidental recursion, duplicate publication, swallowed failure, or ACK-on-error behavior.

## 5. Pure Decision Contract

Policy input:

```text
command
+ current counter/state snapshot
+ ordered alert configuration
```

Policy output:

```text
AlertTransition
  counter_value?
  state_name?
  domain_events[]
  device_refresh_targets[]
  no_op_reason?
```

Policy must not import Django ORM, settings, RabbitMQ, MQTT, Redis, admin, or request objects. Time-dependent scheduler decisions receive time/config explicitly.

## 6. Application Transaction [P4]

Target execution:

```text
begin transaction
-> lock alert aggregate/version row or equivalent serialization point
-> reject already processed idempotency key
-> load current counter and ordered states
-> run AlertPolicy
-> persist counter snapshot when changed
-> update exactly one current state when changed
-> append required alert AuditEvent rows
-> append device-refresh OutboxMessage rows
-> record command result/idempotency
-> commit
```

No direct publisher call occurs inside policy, repository, model `save()`, or transaction callback. Outbox worker handles delivery after commit.

## 7. Concurrency Policy [P4]

Alert changes serialize on one singleton alert aggregate row locked with `select_for_update()`. The aggregate owns a non-null current-state reference; P4 keeps legacy `AlertState.current` flags synchronized for database and fixture compatibility.

Do not rely on reading latest `AlertCounter` and writing a new row without the aggregate lock. Two concurrent increments must preserve both operations in committed order.

The aggregate reference plus transaction logic must enforce exactly one current alert state. P4 data migration must fail visibly rather than guess when legacy data has zero or multiple current rows.

## 8. Entry Adapters [P4]

### Admin

- “Set active” action calls `AlertService`.
- Counter adjustment action/form calls same service.
- Operator user ID becomes actor/audit metadata.
- Admin never updates `current` flags directly.
- Service result and downstream delivery status are visible separately.

### Rabbit worker

- Consume dedicated alert command queue/binding.
- Validate versioned envelope and payload.
- ACK committed success or idempotent duplicate.
- Retry transient database/infrastructure failure.
- Dead-letter invalid/poison command with diagnostic metadata.
- Never consume or ACK device/terminal/unrelated internal traffic.

### Scheduler

- Evaluate due time under explicit scheduler ownership/lock.
- Enqueue one idempotent alert command.
- Do not change alert models directly.
- Record skipped/invalid configuration visibly.

### MQTT ingress

- Decode complete device packet in transport layer.
- Translate allowed alert `INFO` input into alert command.
- Keep original device ID, event source, timestamp, task ID, and correlation metadata.
- Do not invoke worker callback in-process as alternate semantics.

## 9. Domain Events [P4]

Minimum committed event types:

- `alert.counter_changed`
- `alert.state_changed`
- `operator.alert_state_requested`
- `scheduler.alert_change_requested` where audit requires request visibility

P4 records alert control-plane history as `AuditEvent` and publishes compatible domain-event work through the outbox. P5 may additionally append player/game-relevant alert facts as session-scoped `GameEvent` rows. Absence of a session must not fabricate a `GameEvent.session_id`.

Refresh work should be explicit outbox commands, for example:

- `device.refresh_requested` with target `scl/all`;
- `device.refresh_requested` with active topic snapshot or a deterministic resolver policy.

Whether active-topic membership is captured at transaction time or resolved at delivery time remains `Unverified / Decision Required`. P4 cutover is blocked until the owning work package records and tests one choice.

## 10. Minimum Tests [P3/P4]

- Set/increase/decrease success and no-op.
- Exact threshold lower/upper boundaries.
- Characterize current negative and above-maximum counter outcomes in P3; replace this characterization with named accepted outcomes before P4 cutover.
- State request found succeeds; unknown state is rejected without state/history/outbox changes.
- Counter reset enabled/disabled and unchanged threshold.
- Auto-increase/decrease and dampening follow characterized boundaries; disabled configuration is a visible no-op; invalid mode is rejected without stopping the scheduler process.
- Two concurrent increments preserve both operations.
- Duplicate command ID changes state once.
- Transaction rollback leaves no state/history/outbox partials.
- State change writes history and refresh outbox atomically.
- Admin calls service with operator actor; no direct model mutation.
- Scheduler emits one idempotent command per due interval.
- MQTT and Rabbit envelope round trips preserve source/actor/correlation.
- Broker unavailable after commit leaves retryable outbox row.
- Worker settlement: success ACK, transient retry, invalid DLQ.
- Legacy/new policy comparison against recorded sequences.

P3 shadow tests must prove no state write, history append, outbox append, broker publication, device refresh, or message-settlement effect occurs. Legacy execution remains the sole side-effect owner.

## 11. Cutover Gate [P4]

Alert runtime may cut over only when:

- every current alert entrypoint invokes one service;
- model saves no longer publish alert events for migrated writes;
- queue binding cannot receive unrelated traffic;
- state/history/outbox transaction and concurrency tests pass;
- exactly one aggregate-selected current state exists and legacy flags match it;
- publisher confirmation/retry/DLQ are operational;
- device refresh fanout matches captured legacy expectations;
- scheduler behavior and restart semantics are covered;
- operator admin provides required alert control;
- rollback can re-enable legacy process without replaying already committed commands incorrectly.

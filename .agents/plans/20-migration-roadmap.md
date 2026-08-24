# Migration Roadmap

Reviewed: 2026-08-24
Status: proposed
Depends on: `00-source-assessment.md`, `10-target-architecture.md`, `15-foundation-and-tooling.md`

## 1. Strategy

Use vertical slices and compatibility gates. Extraction may precede cutover. Runtime replacement happens only after complete entrypoint, queue, persistence, side-effect, and failure-path parity.

```text
characterize
-> extract policy/DTO/repository
-> route one adapter through service
-> add transaction/history/outbox
-> shadow or replay verification
-> cut over
-> observe
-> remove legacy path
```

## 2. Phase Overview

| Phase | Goal | Depends on | Cutover allowed? |
| --- | --- | --- | --- |
| P0 | Baseline and recovery safety | current reviews | no |
| P1 | Foundation/tooling/bootstrap | P0 | no |
| P2 | Admin-first HTTP surface and DRF removal | P1 | HTTP only after consumer proof |
| P3 | Alert extraction pilot | P1 | no worker cutover yet |
| P4 | Transactional outbox and Rabbit reliability | P3 | alert cutover after gates |
| P5 | Game history/feed/operator projections | P4 | stream migration after data verification |
| P6 | Remaining vertical slices | P4/P5 as applicable | slice by slice |
| P7 | Legacy cleanup and package consolidation | all parity gates | yes |

## 3. P0 — Baseline and Recovery Safety

Work:

- Inventory deployed API, admin, terminal, MQTT, and database consumers.
- Capture representative production-compatible configuration without secrets/runtime noise.
- Export database and media backup; document restore test.
- Capture golden PING/PONG/CUP/SUP/INFO packets per device type.
- Record Rabbit topology and deployed firmware/client versions.
- Measure stream/game-history volume and identify player/operator consumers.
- Turn current `.agent-review` minimum tests into characterization backlog.
- Define migration feature flags or process-level rollback points.

Exit:

- Restore procedure tested.
- Canonical device/game flows reproducible locally or through simulator.
- API removal consumers explicitly confirmed absent or migrated.
- Data and wire contracts marked preserve/change/unknown.

## 4. P1 — Foundation, Tooling, and Bootstrap

Execute `15-foundation-and-tooling.md`.

Additional work:

- Fix WSGI/entrypoint/settings path before architectural cutover.
- Make integrity checks non-mutating by default; move repair to explicit command.
- Ensure migrations run before checks requiring migrated tables.
- Add graceful signals/drain skeleton to long-lived processes.

Exit:

- Clean-checkout setup, lint, test, smoke, migration, and admin boot pass.
- Current legacy runtime still works while new application layers are introduced.

## 5. P2 — Admin-First HTTP Surface

Work:

- Verify no terminal/device/operator client requires legacy REST routes.
- Make Django admin authoritative operator surface.
- Add explicit roles and action permissions.
- Move important stateful admin actions behind application services.
- Replace mutating health checks with read-only liveness/readiness.
- Move repair/import/update operations to audited admin actions or management commands.
- Remove API routers/views/serializers/schema/auth/CORS dependencies in controlled steps.
- Keep media/static URLs required by terminals stable.

Exit:

- No observed or declared consumer depends on removed endpoints.
- Admin covers alert, devices, behavior/access, terminals, assets, game history, and required operations.
- Fresh dependency install and production WSGI boot without DRF/Spectacular.
- Access secrets are masked and destructive cascades are constrained/visible.

## 6. P3 — Alert Extraction Pilot

Execute `30-alert-pilot.md` without changing queue ownership initially.

Work:

- Extract DTOs, pure policies, repository, and application service.
- Route admin and characterized direct call sites through service in test/shadow mode.
- Preserve legacy worker entrypoint until reliable event infrastructure exists.
- Compare old/new decisions against captured alert sequences.

Exit:

- Alert rule tests cover success, no-op, threshold edges, invalid config, ordering, and concurrency decisions.
- New service has no direct Rabbit/MQTT publication.
- Old and new policy results match preserved contracts or intentional differences are approved.

## 7. P4 — Reliable RabbitMQ Boundary and Alert Cutover

Execute event/outbox parts of `40-game-events-and-rabbitmq.md`.

Work:

- Add domain command/event envelopes and schema versions.
- Add outbox, publisher confirmation, bounded retry, DLQ, and metrics.
- Create dedicated queues/bindings by responsibility.
- Add idempotent consumer receipts or projection uniqueness.
- Make alert transaction persist state, game/audit events, and outbox atomically.
- Make consumer ACK follow committed success; define reject/retry/poison outcomes.
- Cut scheduler/admin/MQTT alert paths to one application service.
- Remove alert model-save and legacy context publication only after parity.

Exit:

- Broker outage cannot silently lose committed required work.
- Duplicate delivery does not duplicate state/history/projections.
- Non-alert events cannot be consumed by alert worker.
- Alert cutover survives rollback, retry, restart, and concurrent command tests.

## 8. P5 — Game History, Player Feed, and Operator Monitoring

Execute remaining `40-game-events-and-rabbitmq.md`.

Work:

- Add `GameSession`, append-only `GameEvent`, and explicit sequence allocation.
- Build player-safe feed projection and operator monitoring projection.
- Deliver terminal feed through compatible MQTT snapshot/delta contract or a separately justified narrow read endpoint.
- Separate operational logs/metrics from game events.
- Map/import useful legacy `StreamRecord` history without fabricating missing identity/session data.
- Add retention, redaction, archive/export, and read-only admin policy.

Exit:

- One complete game session can be reconstructed from durable history.
- Player view shows only allowed events in deterministic order.
- Operator can inspect session state/history and failed delivery without editing facts.
- Legacy stream readers and historical data have explicit migration outcome.

## 9. P6 — Remaining Vertical Slices

Recommended order:

1. Lock access and player identity/code validation.
2. Device desired/reported state plus CUP/SUP delivery.
3. Generic MQTT ingress, keepalive, PING/PONG, and reconciliation.
4. Terminal account/menu/content and player feed delivery.
5. Assets/blob lifecycle and URLs.
6. Passive device configuration.
7. Scheduler tasks beyond alert auto-change.
8. Imports, integrity repair, and operational administration.

For every slice:

- read nearest `.agent-review`;
- list entrypoints, persistence, events, side effects, and wire formats;
- create policy/DTO/repository/service/adapters;
- add transaction/outbox where required;
- add unit, repository, admin, worker, broker, and wire tests;
- shadow/replay when possible;
- cut over one entrypoint set;
- observe and reconcile;
- remove old code only after no consumers remain.

## 10. P7 — Cleanup

Work:

- Remove dead DRF/API/schema/auth/CORS code and dependencies.
- Remove legacy event contexts/handlers replaced by services.
- Remove model-save network side effects and compatibility switches.
- Replace/drop generic stream tables only after archive/migration.
- Remove duplicated transport definitions and unused scheduler paths.
- Clean runtime state from seed fixtures.
- Consolidate package layout while preserving Django app labels/migration graph.
- Update root and child `.agent-review` files to target behavior.

Exit:

- One code path owns each command/event/side effect.
- No production process imports removed legacy modules.
- No compatibility flag remains without owner and expiry.
- Full test, migration, broker, simulator, startup, shutdown, backup, and restore suite passes.

## 11. Global Stop Conditions

Pause cutover when any occurs:

- Unknown real consumer of route, table, media URL, topic, or packet.
- Missing database/media backup or untested restore.
- New consumer shares broad queue with incompatible messages.
- Required publication lacks confirmation/retry/reconciliation.
- Source ACK can occur before required transaction commits.
- Data migration cannot preserve identity/order/history semantics.
- Simulator/golden payload differs from deployed device behavior.
- Admin workflow loses required operator capability.


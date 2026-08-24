# Migration Roadmap

Reviewed: 2026-08-25
Status: accepted
Role: roadmap baseline
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

## 2.1 Work Package Register

This file is the sole ordering authority. Each work package names its owner, dependency, deliverable, preserved contract, verification, cutover, and rollback boundary.

| ID | Owner / depends on | Deliverable | Preserve / verify | Cutover / rollback |
| --- | --- | --- | --- | --- |
| `P0-W1` | migration lead / current reviews | consumer, backup, compatibility, and workload evidence | deployed DB/wire/media behavior / restore plus replay evidence | no cutover / no runtime change |
| `P1-W1` | platform / `P0-W1` | deterministic environment, commands, CI feedback, and bootstrap | legacy runtime / clean-checkout smoke | no cutover / restore prior tooling entrypoint |
| `P2-W1` | web/admin / `P1-W1` | authenticated admin foundation and route-consumer decision | operator capability / role and route tests | secure HTTP surface / restore protected legacy route |
| `P2-W2` | web/admin / `P2-W1` | controlled REST/DRF removal | proven terminal/media access / WSGI and admin smoke | remove only unconsumed routes / restore compatibility adapter |
| `P3-W1` | alert / `P1-W1` | DTO, pure policy, repository seam, and characterization | alert decisions / policy comparison | no cutover / legacy remains owner |
| `P3-W2` | alert / `P3-W1` | non-mutating shadow comparison | legacy state and effects / captured-sequence parity | no cutover / disable shadow capture |
| `P4-W1` | messaging / `P3-W2` | event/outbox foundation and reliable Rabbit boundary | legacy wire routes during transition / broker failure tests | new reliable queues / restore isolated legacy consumers |
| `P4-W2` | alert / `P4-W1` | adapter-by-adapter alert cutover | alert/device behavior / rollback, replay, concurrency tests | one entrypoint set at a time / re-enable legacy owner |
| `P5-W1` | history / `P4-W1` | game sessions, history, and projections | player/operator semantics / rebuild tests | new read models / restore compatibility reader |
| `P5-W2` | history / `P5-W1` | reconciled legacy stream migration/archive | legacy record identity/content / count and sample reconciliation | switch verified readers / restore archive reader |
| `P6-W1` | devices / `P4-W1` | lock identity, liveness, and reported state | MAC, CUP/SUP, no-echo behavior / device replay | lock slice only / legacy handlers |
| `P6-W2` | assets / `P2-W2` | storage compatibility and recovery behavior | UUIDs, blobs, media consumers / DB-media manifest | verified storage path / legacy read fallback |
| `P6-W3` | behavior / `P6-W1`, `P6-W2` | access, menu, account ordering, and revisions | ACL/menu/account payloads / golden projection tests | behavior slice / legacy projection |
| `P6-W4` | terminals / `P6-W3` | terminal projection and delivery | terminal payloads/media access / client replay | terminal slice / legacy delivery |
| `P6-W5` | devices / `P6-W1` | passive configuration | passive payloads / device fixtures | passive slice / legacy builder |
| `P6-W6` | scheduler / migrated slice services | remaining scheduled commands | cadence and restart behavior / task characterization | task by task / legacy scheduled task |
| `P6-W7` | operations + behavior / `P6-W3` | safe imports and repair operations | CSV/access relationships / atomicity and permission tests | register safe route/command / disable entrypoint |
| `P7-W1` | migration lead / all parity gates | remove explicitly deferred compatibility paths and consolidate packages | IDs, migrations, fixtures, wire formats / full regression suite | final cleanup / restore last compatible release |

## 3. P0 — Baseline and Recovery Safety

Work:

- Inventory deployed API, admin, terminal, MQTT, and database consumers.
- Capture representative production-compatible configuration without secrets/runtime noise.
- Export database and media backup; document restore test.
- Capture golden PING/PONG/CUP/SUP/INFO packets per device type.
- Record Rabbit topology and deployed firmware/client versions.
- Measure stream/game-history volume and identify player/operator consumers.
- Record workload discovery for relevant flows: message volume/bursts, payload sizes, device fanout, queue lag, DB latency, and backfill volume where observable. Unknown values remain explicit evidence gaps, not invented targets.
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
- Establish secure admin registrations, roles, read-only diagnostics, and action inventory. Stateful actions move behind application services in their owning domain phases; P2 does not invent temporary domain services.
- Replace mutating health checks with read-only liveness/readiness.
- Move repair/import/update operations to audited admin actions or management commands.
- Remove API routers/views/serializers/schema/auth/CORS dependencies in controlled steps.
- Keep media/static URLs required by terminals stable.

Exit:

- No observed or declared consumer depends on removed endpoints.
- Admin securely covers the required operator inventory and existing capabilities; service-backed stateful actions are tracked by owning slice work packages.
- Fresh dependency install and production WSGI boot without DRF/Spectacular.
- Access secrets are masked and destructive cascades are constrained/visible.

## 6. P3 — Alert Extraction Pilot

Execute `30-alert-pilot.md` without changing queue ownership initially.

Work:

- Extract DTOs, pure policies, repository, and application service.
- Capture inputs from admin and characterized direct call sites, run the new pure policy in non-mutating shadow mode, and compare results. Legacy code remains the only owner of writes and side effects.
- Preserve legacy worker entrypoint until reliable event infrastructure exists.
- Compare old/new decisions against captured alert sequences.

Exit:

- Alert rule tests cover success, no-op, threshold edges, invalid config, ordering, and concurrency decisions.
- New service has no direct Rabbit/MQTT publication.
- Shadow execution creates no domain writes, history, outbox work, publication, or settlement effects.
- Old and new policy results match preserved contracts or intentional differences are approved.

## 7. P4 — Reliable RabbitMQ Boundary and Alert Cutover

Execute event/outbox parts of `40-game-events-and-rabbitmq.md`.

Work:

- Add domain command/event envelopes and schema versions.
- Add outbox, publisher confirmation, bounded retry, DLQ, and metrics.
- Create dedicated queues/bindings by responsibility.
- Add idempotent consumer receipts or projection uniqueness.
- Make alert transaction persist state, required audit/domain-event records, and outbox atomically. Session-scoped `GameEvent` integration belongs to P5.
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

1. Lock identity, liveness, reported state, and access behavior.
2. Asset storage compatibility, blob lifecycle, and media URLs.
3. Behavior/access, menu/account ordering, and configuration revisions.
4. Terminal projection, content, player feed, and delivery.
5. Passive device configuration.
6. Scheduler tasks beyond alert auto-change.
7. Imports, integrity repair, and operational administration.

P6 prerequisites and ownership:

- CSV parsing, validation, authorization, audit, and atomic persistence must exist before registering the import route.
- `admin_extended` owns protected upload UI and parsing; the behavior slice owns user/access persistence and duplicate policy.
- Asset cutover requires documented storage failure/recovery behavior and a database-to-blob compatibility manifest.
- Device fanout behavior, target selection, partial failure reporting, and retry ownership must be decided before replacing legacy delivery.
- Each slice moves its own stateful admin actions behind its application service; P2 provides only the secure admin foundation.

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

- Remove only compatibility adapters and legacy routes explicitly deferred by an owning phase after their consumers are gone; do not repeat dependency removal owned by an earlier phase.
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

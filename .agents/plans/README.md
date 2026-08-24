# SKABEN Migration Plans

Reviewed: 2026-08-24
Status: proposed migration baseline
Scope: migration of the current SKABEN repository toward a layered, testable Django control plane

## Purpose

This directory turns three sources of information into one executable migration plan:

1. The current repository and `server/**/.agent-review` files describe behavior that exists today.
2. `/home/zerthmonk/projects/template` provides target conventions for packaging, tooling, tests, settings, and layered application code.
3. `/home/zerthmonk/skaben_refactor_reference` provides a partially implemented alert migration and evidence about useful extraction seams.

Code and current `.agent-review` files remain authoritative for existing behavior. The template and partially migrated repository are design inputs, not compatibility specifications.

## Read Order

1. `server/.agent-review`
2. Nearest relevant child `.agent-review`
3. `00-source-assessment.md`
4. `10-target-architecture.md`
5. `15-foundation-and-tooling.md`
6. `20-migration-roadmap.md`
7. Slice-specific plans:
   - `30-alert-pilot.md`
   - `40-game-events-and-rabbitmq.md`

When implementing a phase, read only its dependencies and the `.agent-review` files for touched areas.

## Fixed Decisions

These decisions supersede incompatible assumptions in older plans:

- Keep Django, its ORM, migrations, authentication, management commands, and server-rendered admin.
- Treat Django admin as the operator configuration and control interface.
- Remove the unused public/operator REST API and DRF stack after consumer verification.
- Do not replace DRF with Django Ninja unless a new, concrete HTTP consumer appears.
- Do not build the abandoned Vue operator panel as part of this migration.
- Keep PostgreSQL as authoritative state and history storage.
- Keep RabbitMQ for internal delivery and MQTT for physical devices.
- Introduce a transactional outbox before relying on asynchronous side effects.
- Replace the generic `streams` implementation with explicit game history, player feed, operator monitoring, and operational-observability boundaries.
- Use a modular monolith with separate runtime processes. Do not split deployables or introduce Kafka/TimescaleDB without measured need.
- Preserve existing database identifiers, migrations, fixture compatibility, MQTT routing, device payloads, and confirmed game rules.

## Plan Map

| Document | Purpose | Main outputs |
| --- | --- | --- |
| `00-source-assessment.md` | Classify reusable and unsafe material | adopt/adapt/reject decisions |
| `10-target-architecture.md` | Define final boundaries and runtime flow | package ownership, dependency rules, process topology |
| `15-foundation-and-tooling.md` | Adopt useful template/P0 engineering practices | supported environment, lint, tests, CI, bootstrap |
| `20-migration-roadmap.md` | Order implementation phases | dependencies, exit criteria, cutover gates |
| `30-alert-pilot.md` | Use alert as first complete vertical slice | pure rules, repository, service, admin/worker adapters |
| `40-game-events-and-rabbitmq.md` | Define reliable history and event distribution | game events, outbox, RabbitMQ topology, projections |

## Planning Vocabulary

- **Command:** request to change state, such as increasing the alert counter or opening a lock.
- **Domain event:** immutable fact that has occurred, such as `alert.state_changed` or `lock.opened`.
- **Effect:** explicit work requested by a pure policy, such as persisting state, recording an event, or requesting device refresh.
- **Outbox message:** committed database record waiting for confirmed RabbitMQ publication.
- **Projection:** read model derived from domain events for player feed or operator monitoring.
- **Transport event:** RabbitMQ/MQTT envelope used to deliver a command or domain event.
- **Operational log:** diagnostic record about software or infrastructure, not game history.

## Change Rules

1. Migrate one vertical slice at a time.
2. Characterize current behavior before replacing it.
3. Keep model/schema migration separate from application-layer extraction where possible.
4. Do not activate a narrow consumer on a broad shared queue.
5. Do not acknowledge required work before its transaction commits.
6. Do not publish required messages directly from model `save()` methods.
7. Preserve wire compatibility until real devices pass replay/simulator tests.
8. Keep observed behavior and target behavior explicit in tests and migration notes.
9. Remove legacy code only after entrypoint, data, queue, and side-effect parity is proven.

## Completion Definition

Migration is complete when:

- supported runtime commands boot deterministically from one settings contract;
- operator work is available through authenticated Django admin;
- DRF, obsolete API routes, schema generation, and abandoned frontend scaffolding are removed;
- domain decisions live in testable services/policies rather than models or transport handlers;
- PostgreSQL transactions create required domain history and outbox work atomically;
- RabbitMQ delivery has publisher confirmation, retry, DLQ, idempotency, and observable settlement;
- game history, player feed, operator monitoring, and operational logs have separate owners;
- every device packet and routing contract has compatibility coverage;
- legacy handlers, contexts, and model-save side effects have no remaining runtime consumers.


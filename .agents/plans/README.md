# SKABEN Migration Plans

Reviewed: 2026-08-25
Status: accepted
Role: migration baseline
Scope: migration of the current SKABEN repository toward a layered, testable Django control plane

## Purpose

This directory turns three sources of information into one executable migration plan:

1. The current repository and `server/**/.agent-review` files describe behavior that exists today.
2. `/home/zerthmonk/projects/skaben` provides target conventions for packaging, tooling, tests, settings, and layered application code.
3. `/home/zerthmonk/projects/skaben_refactor_ref` provides a partially implemented alert migration and evidence about useful extraction seams.

Code and current `.agent-review` files remain authoritative for existing behavior. The template and partially migrated repository are design inputs, not compatibility specifications.

## Authority

When sources disagree, use this order:

1. Current code, migrations, deployment entrypoints, and confirmed deployed observation define current behavior.
2. The nearest `server/**/.agent-review` summarizes current behavior; it does not override code.
3. Fixed decisions in this file define accepted migration direction.
4. `10-target-architecture.md` owns target boundaries and process topology.
5. `20-migration-roadmap.md` owns phase order and cutover sequencing.
6. Slice plans own implementation detail inside their assigned roadmap phases.

Candidate target mappings and roadmap references in child reviews are non-authoritative. Higher-authority planning documents win; unresolved conflicts block implementation until recorded in the owning plan.

Status vocabulary:

- `verified-current`: current-state review content agrees with its scoped `source_digest`;
- `stale`: scoped code changed after review and requires rechecking before routed use;
- `proposed`: planning content awaiting acceptance;
- `accepted`: approved implementation direction;
- `superseded`: retained only for history.

## Source Registry

| Name | Location | Reviewed revision | Role |
| --- | --- | --- | --- |
| `current_skaben` | `/home/zerthmonk/projects/old-skaben` | `c81012250d4b67d668b3537c4bbd14e83d56b954` | authoritative current implementation |
| `refactor_reference` | `/home/zerthmonk/projects/skaben_refactor_ref` | `b5b1d399ef2319e57917ed9a6b23c41c4fe77007` | prototype extraction evidence |
| `template` | `/home/zerthmonk/projects/skaben` | `1186a40cb41d5ebd1c8b604a9aa808a0bebdcacc` | engineering-convention input |

Do not use shorthand source names that are absent from this registry.

## Onboarding Read Order

Use this sequence to understand the complete migration baseline, not as the default context bundle for an implementation task:

1. `server/.agent-review`
2. Nearest relevant child `.agent-review`
3. `00-source-assessment.md`
4. `10-target-architecture.md`
5. `15-foundation-and-tooling.md`
6. `20-migration-roadmap.md`
7. Slice-specific plans:
   - `30-alert-pilot.md`
   - `40-game-events-and-rabbitmq.md`

## Task Read Algorithm

For a scoped implementation task:

1. Name each owning work package and every intended/touched path before work begins.
2. Run `python .agents/context_loader.py render --work-package <ID> --path <path>`;
   repeat both flags when a task spans packages or paths.
3. Classify the task against each matched condition's `apply_when` rule and pass every
   applicable semantic flag as `--condition <name>`. Path-decidable conditions are added
   automatically.
4. Read the rendered authority summary, shared current context, active roadmap sections,
   required route sections, phase-owned target sections, and selected conditional sections.

The loader derives phases from explicit work-package IDs and keeps no global active state.
It accepts routed future paths before those files exist, but rejects unknown packages,
conditions, absolute/outside-repository paths, unmatched paths, and selected stale reviews.
After plans, reviews, routing, or the bootstrap change, run
`python .agents/context_loader.py check` locally.

`Depends on` records authority and implementation order; it does not recursively expand task context. Provenance is never a required-read dependency. When multiple exact routes match, combine their selected sections without loading their parent reviews automatically.

Routing references use exact files plus Markdown heading sections and phases. A selector matches either a complete heading or its unique label after an optional numeric prefix such as `4.`; a section ends at the next heading of equal or higher level. Wildcards are allowed only in `match` path selectors, never in review or plan dependencies. Missing or ambiguous paths, headings, phases, or symmetric cross-review dependencies make the routing manifest invalid.

`source_revision` records review provenance. `source_digest` deterministically detects
changes to the review's tracked runtime scope; tests, reviews, caches, and generated
artifacts are excluded, while migrations and runtime templates remain included.

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

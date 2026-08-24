# Migration Source Assessment

Reviewed: 2026-08-25
Status: accepted
Role: planning input
Derived from: current-state reviews routed by `../context-routing.yml`
Required implementation context: `README.md` plus the route selected by `../context-routing.yml`

## 1. Source Priority

| Priority | Source | Use |
| --- | --- | --- |
| 1 | Current SKABEN code and migrations | authoritative observed behavior and data contracts |
| 2 | Current `server/**/.agent-review` | reviewed flow, failure, compatibility, and gap map |
| 3 | `refactor_reference/app` | tested extraction patterns and alert behavior candidate |
| 4 | `refactor_reference/server-middle` | frozen legacy comparison snapshot only |
| 5 | `refactor_reference/.agents/plans` | historical design intent; selectively adopted |
| 6 | `template` | target engineering conventions; selectively adopted |

Do not use `server-middle` as a source of newer behavior. It is nearly a copy of the legacy server created during the alert experiment. The partially migrated `app` still imports active legacy models through `PYTHONPATH=server`.

`refactor_reference` and `template` resolve through the canonical source registry in `README.md`.

## 2. Useful History from `refactor_reference`

The partial migration was produced in three commits on 2026-07-12:

1. Tooling/environment and initial `app` scaffold.
2. Alert DTO, repository, state-machine, and adapter extraction.
3. App-owned RabbitMQ helpers, alert worker, MQTT ingestion, scheduler, admin, and tests.

This concentrated history makes it a prototype rather than a deployment-proven branch. Reuse design and tests after checking them against current code; do not merge the branch wholesale.

## 3. Adopt from `refactor_reference`

| Candidate | Why useful | Target use |
| --- | --- | --- |
| Pure alert transition functions | Rules run without Django requests or Kombu messages | first vertical-slice policy layer |
| Immutable snapshot DTOs | Make state/config inputs explicit | service input boundary |
| Explicit effect DTOs | Reveal persistence, refresh, and log decisions | evolve into commands/domain events/outbox work |
| Repository over legacy models | Allows logic extraction before schema relocation | temporary persistence seam |
| `bulk_create()`/`update()` for migrated writes | Avoids legacy model `save()` publication hooks | controlled transition mechanism |
| Thin scheduler adapter | Separates timing from alert decision | scheduler emits command only |
| Dedicated management commands | Makes process ownership explicit | one command per worker/scheduler role |
| App-focused tests | Characterize rule and adapter behavior | move and expand under owning slice |
| DRF-free worker settings | Proves worker runtime need not load HTTP stack | settings profiles or common settings without DRF |
| Explicit Rabbit initialization at startup | Avoids broker work in `AppConfig.ready()` | infrastructure bootstrap rule |

## 4. Adapt from `refactor_reference`

| Candidate | Problem in prototype | Required adaptation |
| --- | --- | --- |
| Generic `app/` package | Becomes a second architecture beside domain apps | place DTO/service/repository code under owning domain slices or a clearly named application package |
| Alert repository | Individual effects are not one transaction; concurrent snapshots can race | add unit-of-work transaction, row locking/version checks, and event/outbox persistence |
| Effect executor | Interleaves DB writes and direct broker publication | persist state/history/outbox first; publish later |
| MQ module copy | Duplicates legacy transport and still swallows failures | establish one infrastructure implementation with typed outcomes |
| Alert worker | Consumes broad `internal` queue and ACKs unsupported messages | dedicated binding/queue and typed retry/discard policy |
| MQTT alert worker | Replaces generic ingress while supporting only alert `INFO` | keep complete ingress router or introduce non-overlapping bindings during migration |
| Minimal admin | Registers only alert state/counter and bypasses services | register every required configuration area and invoke application services for actions |
| Worker-focused settings | Used accidentally as web settings in prototype | define explicit common/web/worker/test profiles or one coherent admin-first runtime |
| Stream repository | Persists only operational logs in generic stream table | replace with game-event/outbox/projection boundaries |
| Test suite | Strong units but mocked publication and incomplete failure coverage | add integration, settlement, concurrency, rollback, and wire tests |

## 5. Reject from `refactor_reference`

- Running narrow consumers on broad shared queues.
- Acknowledging unsupported or failed internal messages unconditionally.
- Catching publisher exceptions and returning implicit success.
- Direct synchronous publication from an effect executor.
- Treating generic stream-log persistence as migrated game history.
- Keeping three long-lived code copies: `app`, `server`, and `server-middle`.
- Replacing production entrypoints before bootstrap and Compose parity exist.
- Removing dependencies while the legacy WSGI/entrypoint still imports them.
- Using `server-middle` as an ongoing migration source.

## 6. Adopt from the Template

| Candidate | Adoption rule |
| --- | --- |
| Repository/service/adapter or handler separation | apply per domain slice, without repository wrappers that merely rename ORM calls |
| `uv` and `pyproject.toml` ownership | use one lockfile and one documented environment |
| Ruff, mypy, Flake8/WPS, pytest, coverage, factories | introduce with a staged baseline; new code must pass full target suite |
| Typed environment parsing | use for secrets, hosts, ports, timeouts, and feature flags |
| Explicit Gunicorn/WSGI bootstrap | keep one importable production path with smoke test |
| Organized tests beside owning packages | include unit, repository, adapter, and integration layers |
| Central exception/result conventions | use typed application/infrastructure failures |
| Makefile command surface | provide short canonical setup, lint, test, migration, admin, worker, and Compose commands |

## 7. Do Not Copy Blindly from the Template

- Django Ninja/API examples: current target has no public operator API.
- Template frontend/Jinja integration: not required for Django admin control plane.
- Permissive security defaults such as wildcard hosts/CORS or fallback secrets.
- Template version inconsistencies. Choose and test one Python/Django pair explicitly.
- Template deployment filenames/commands without verifying this repository's Docker layout.
- Template business examples, response semantics, or absent authorization policy.

## 8. Historical Plan Triage

| `refactor_reference` plan | Disposition |
| --- | --- |
| Architecture audit | Retain findings already covered by current `.agent-review`; current reviews take precedence |
| P0 runtime/tooling | Adopt supported `uv`, split runtime/tooling commands, smoke checks, and discoverable workflow |
| P1 three-module split | Adapt into domain slices plus shared infrastructure; retain pure state machine and thin adapters |
| Configuration API | Replace with authenticated Django admin plus application services |
| Django Ninja migration | Reject until a real API consumer exists |
| Vue/Vite frontend | Reject for current scope |
| TimescaleDB ingestion | Defer until measured telemetry volume and query requirements justify it |

## 9. Main Lesson

The partial repository proves alert logic can be separated without moving legacy tables first. It also proves that code extraction and runtime cutover are different operations. Future slices may copy the extraction technique, but a runtime process must not replace its legacy counterpart until queue, packet, settlement, scheduler, admin, and side-effect parity are complete.

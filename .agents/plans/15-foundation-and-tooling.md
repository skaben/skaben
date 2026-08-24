# Foundation and Tooling Plan

Reviewed: 2026-08-25
Status: accepted
Role: foundation baseline
Depends on: `00-source-assessment.md`, `10-target-architecture.md`

## 1. Objective

Adopt useful engineering practices from `template` and `refactor_reference` before large behavior changes. These names resolve through the source registry in `README.md`. Foundation work must create trustworthy feedback without silently changing game, database, or wire contracts.

## 2. Supported Environment

Use the current locked repository matrix for P1:

- Python 3.12.x;
- Django 5.0.3;
- `uv` with committed `uv.lock` as dependency authority;
- PostgreSQL, Redis, and RabbitMQ in Docker;
- host-native lint/tests allowed through documented environment values;
- application processes remain available through Docker Compose.

Changing the Python minor line, Django version, or dependency authority requires a separate accepted upgrade decision; P1 does not perform that upgrade implicitly.

Do not combine Python/Django major upgrades, DRF removal, package relocation, and domain extraction in one change.

## 3. Dependency Cleanup Ownership

P1 inventories API imports, runtime consumers, settings, routes, and startup dependencies. It does not remove DRF or API code. After P0 consumer verification, P2 owns removal of:

- `djangorestframework`;
- `rest_framework.authtoken` application configuration;
- `djangorestframework-jwt`;
- `django-rest-polymorphic`;
- `drf-spectacular` and sidecar;
- API-only `django-filter` use;
- CORS middleware/settings if no browser client remains.

Do not add Django Ninja. Keep `django-polymorphic` only while menu/content models require it. Review authentication-token tables in a later schema migration rather than coupling table deletion to dependency removal.

P1 must leave the characterized legacy HTTP runtime bootable. Its output is a dependency/removal inventory consumed by P2.

## 4. Tool Suite

Adopt from the template, with settings made consistent for this repository:

| Tool | Purpose | Rollout |
| --- | --- | --- |
| Ruff check/format | fast correctness, imports, modernization, formatting | full for new code; baseline legacy violations |
| mypy | type boundaries around DTOs/services/repositories | strictest first on new application code |
| Flake8/WPS | complexity and maintainability pressure | apply to migrated code; tune documented exceptions |
| pytest + pytest-django | unit/repository/admin/integration tests | canonical test runner |
| pytest-cov/coverage | migration confidence and missing paths | report by slice, not vanity global threshold initially |
| factory-boy | stable model/test construction | replace large ad hoc fixture setup |
| pytest-timeout | catch dead worker/scheduler tests | required for process/integration tests |
| pytest-mock | adapter isolation | retain real integration lanes too |
| pre-commit/pre-push hooks | fast local checks | optional install, same commands as CI |

Linter configuration rules:

- One line-length and target Python version across Ruff, Flake8, and mypy.
- Exclude migrations and generated/static artifacts.
- Do not exclude all tests from correctness rules.
- Every ignore must identify scope and reason.
- Do not mass-format legacy code in behavior-changing migration commits.

## 5. Canonical Commands

Expose short Makefile targets backed by the same underlying commands used in CI:

```text
make install
make lint
make format
make test
make test-integration
make test-coverage
make smoke
make infra-start
make app-start
make stop
make migrate
make admin
```

`make smoke` must validate current target runtime, not legacy settings accidentally retained in WSGI or scripts.

## 6. Environment Contract

Use one documented variable vocabulary. Host and Compose values may differ by explicit overrides, not by separate undocumented files.

Required controls:

- no generated production secret key;
- parsed `ALLOWED_HOSTS` and CSRF origins;
- explicit DB/Redis/Rabbit/MQTT hosts and integer ports;
- explicit static/media roots;
- explicit environment mode;
- no wildcard CORS after API removal;
- safe development defaults that cannot be mistaken for production readiness.

Secrets must not appear in fixtures, admin output, logs, or committed environment files.

## 7. Test Layers

| Layer | Runs against | Purpose |
| --- | --- | --- |
| Policy unit | plain Python | domain decisions and effect ordering |
| DTO/schema unit | Pydantic/dataclasses | validation and compatibility |
| Repository | Django test DB | ORM reads, locks, constraints, migrations |
| Admin adapter | Django request/admin test helpers | roles, forms/actions, service invocation |
| Worker adapter | fake message plus real service/repository where practical | settlement and routing |
| Broker integration | RabbitMQ test service | bindings, confirms, retry, DLQ |
| Device contract | golden MQTT packets/simulator | routing and payload compatibility |
| Bootstrap | real settings/commands | imports, migration, WSGI, process startup |

Tests from `/home/zerthmonk/skaben_refactor_reference/app/tests/tests_alert` are useful seeds. Copy their behavioral assertions, then add failure, transaction, concurrency, and settlement cases missing from the prototype.

## 8. CI Gates

Minimum pull-request gates:

1. Lockfile consistency.
2. Ruff format check and lint.
3. mypy for migrated packages.
4. Flake8/WPS for migrated packages.
5. Unit/repository/admin tests.
6. Django startup and migration check.
7. Focused Rabbit/device contract lane when related files change.

Nightly or explicit integration lane:

- PostgreSQL migrations from production-compatible baseline;
- Rabbit queue declaration and publish/consume round trip;
- outbox retry/DLQ behavior;
- device packet replay;
- fixture load and integrity check;
- graceful worker/scheduler shutdown.

## 9. Foundation Exit Criteria

- One documented Python/Django/uv setup works from clean checkout.
- `make lint`, `make test`, and `make smoke` are authoritative and pass.
- WSGI, settings, URLConf, admin, and management commands import through one intended package layout.
- CI uses the same commands and dependency source as local development.
- Legacy linter debt is baselined without weakening checks for new code.
- Current schema/API startup commands and imports are inventoried for P2; P1 removes none of them.
- Infrastructure and application services can be started separately and together.

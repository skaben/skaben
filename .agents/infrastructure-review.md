---
kind: infrastructure-review
status: verified-current
reviewed_at: 2026-08-25
source_revision: eede8a9b51f3c608c21dcfdfbdfa1a4ad09d0947
scope:
  - docker-compose.yml
  - docker/**
  - entrypoint.sh
  - Makefile
  - server/settings.py
  - server/core/urls.py
---
# Infrastructure Review

## Quick Context

- Root Compose stack runs Django API, four queue workers, scheduler, PostgreSQL,
  Redis, RabbitMQ, and nginx.
- One application image supplies API and worker processes. Current Compose requires that
  image to be built separately and then replaces image code with host bind mounts.
- PostgreSQL, Redis, media, and static data have named volumes. RabbitMQ has no volume.
- Highest risks: committed broker credentials, publicly bound infrastructure ports,
  ephemeral RabbitMQ state, broken production WSGI target, and unsafe bootstrap ordering.
- Prometheus/Grafana and pgAdmin material exists under `docker/` but is not integrated
  with the main stack.

## 1. Inventory

| Source | Current responsibility | Main observation |
| --- | --- | --- |
| `docker-compose.yml` | application plus infrastructure topology | mixed development and deployment concerns |
| `docker/Dockerfile` | shared API/worker image | locked Python dependencies; mutable base/tool inputs |
| `entrypoint.sh` | API bootstrap | performs schema, static, integrity, migration, and server startup work |
| `docker/nginx/**` | HTTP reverse proxy and static delivery | HTTP configured; TLS and production media delivery absent |
| `docker/rabbitmq/**` | RabbitMQ plugins, users, permissions, defaults | credentials committed; runtime data not persisted |
| `docker/prom/**` | Prometheus config and RabbitMQ dashboard artifact | no Prometheus, Grafana, or cAdvisor service in root Compose |
| `docker/pgadmin/**` | optional standalone pgAdmin stack | stale external-network assumption and insecure defaults |

## 2. Observed Runtime Topology

```text
host :80/:443
    -> nginx
        -> api:8000

host :5432 -> PostgreSQL
host :5672/:1883/... -> RabbitMQ

RabbitMQ
    -> worker_mqtt
    -> worker_internal
    -> worker_save
    -> worker_send

scheduler -> RabbitMQ
api/workers/scheduler -> PostgreSQL + Redis as their code paths require
```

Networks:

- `network_public`: API, nginx, RabbitMQ.
- `network_backbone`: API, workers, scheduler, PostgreSQL, Redis, RabbitMQ.
- `network_backbone` is not declared `internal`; network naming and isolation rely on
  Compose defaults.

Runtime isolation already exists at process level: each legacy handler and scheduler has
its own service. This aligns with separate-process target direction, though role names and
responsibilities remain legacy.

## 3. Image Build and Reproducibility

Confirmed strengths:

- Python 3.12 base matches accepted P1 baseline.
- `uv sync --frozen` uses committed `uv.lock`.
- Virtual environment is built separately then copied into final stage.
- `.env` is excluded from image context and Git.

Defects and risks:

1. Root Compose declares `image: skaben-api:latest` without `build`; direct
   `docker compose up` requires a separately built local image. Makefile hides this
   dependency rather than Compose expressing it.
2. API mounts the whole repository over `/opt/app`; workers mount only `server/`.
   Running code therefore differs from immutable image content and differs between API
   and workers.
3. Final image inherits the builder stage, so compiler/build packages remain present; the
   virtual-environment copy is not a lean runtime-stage boundary.
4. Image includes development dependencies.
5. Base inputs `python:3.12-slim-bookworm`, `ghcr.io/astral-sh/uv:latest`, `nginx`,
   `redis:alpine`, `prom/prometheus`, and `dpage/pgadmin4` are not digest-pinned; rebuilds
   can change without repository changes.
6. `.dockerignore` omits `.git`, `.agents`, `.venv`, tests, and other non-runtime inputs.
   It also spells `docker/pg_admin` differently from actual `docker/pgadmin`.
7. Containers run with image-default users; application image defines no non-root user.
8. Builder installs system `python3-psycopg2` while project installs
   `psycopg2-binary`; intent is unclear.

## 4. Startup and Readiness

API dependency gates:

- waits for healthy PostgreSQL and RabbitMQ;
- waits only for Redis container start, not Redis readiness;
- nginx waits only for API container start, not application readiness.

Workers and scheduler depend only on healthy RabbitMQ even though their Django startup and
runtime paths can require PostgreSQL or Redis. `restart: unless-stopped` may eventually
recover some startup races, but does not make bootstrap deterministic.

Current API entrypoint order:

```text
wait_for_db
-> createcachetable
-> collectstatic --clear
-> generate OpenAPI schema
-> mutating check_integrity
-> migrate only when ENVIRONMENT != dev
-> run server
```

Material problems:

- integrity checks run before migrations;
- development startup never applies migrations;
- every API restart mutates static state, cache schema, integrity state, and possibly DB
  migrations;
- multiple API replicas would race the same bootstrap actions;
- `ENVIRONMENT` shell test is unquoted and recognizes only exact `dev`, while Django debug
  selection treats every value not starting with `prod` as debug;
- Gunicorn targets `server.wsgi`, but tracked WSGI module is root `wsgi.py`;
- API has no container healthcheck or graceful-shutdown configuration.

## 5. Persistence and Recovery

| Data | Current storage | Consequence |
| --- | --- | --- |
| PostgreSQL | `db_volume` | survives container replacement |
| Redis AOF | `redis_data` | survives container replacement |
| uploaded media | `files_volume` on API only | durable, but nginx cannot serve volume directly |
| collected static | `static_volume` on API and nginx | shared; rebuilt destructively at API startup |
| RabbitMQ data | container writable layer only | lost when container is removed/recreated |

`make stop` uses `docker-compose down`; `make start` uses `--force-recreate`. With no
RabbitMQ data volume, durable messages, runtime-declared topology, and broker state do not
survive normal stack recreation. Definitions restore users and permissions, but define no
application exchanges, queues, or bindings.

No backup/restore procedure is encoded for PostgreSQL, media, Redis, or RabbitMQ. The DB
mount into `./tmp` is not itself a backup contract.

Production media delivery is incomplete: nginx proxies `/media` to Django but does not
mount `files_volume`; Django's configured static media helper is a development path.

## 6. Network and Secret Boundaries

Root Compose publishes PostgreSQL and RabbitMQ AMQP, MQTT, management, WebSocket, and
metrics ports on host interfaces. Nginx also publishes 443, but no TLS listener or
certificate configuration exists.

RabbitMQ configuration contains committed credentials and password hashes. MQTT, STOMP,
application, and administrator identities receive broad permissions; application and MQTT
users can configure, write, and read all resources. Existing values must be treated as
exposed and rotated rather than merely moved to environment variables.

Additional concerns:

- RabbitMQ debug-level file logging is enabled without visible retention policy.
- Port 8883 is exposed without corresponding TLS listener configuration.
- Django generates a new secret key on each process start, breaking stable signing/session
  behavior across restarts and replicas.
- Development mode enables wildcard hosts and permissive API/CORS behavior; same Compose
  file can start either development or production mode.
- No evidence in repository shows external firewall, TLS termination, or secret injection.

## 7. RabbitMQ Setup

Enabled plugins:

- management;
- MQTT;
- Web STOMP;
- Prometheus metrics.

Healthcheck verifies node ping only. It does not prove definitions loaded, MQTT is ready,
required exchanges/queues exist, or an application publish/consume round trip works.

Current definitions establish users, vhost, permissions, and cluster metadata. Application
code declares operational topology at runtime. Retry queues, DLQs, outbox publication, and
new role-specific P4 queues are not present in Docker configuration yet.

## 8. Nginx Setup

Nginx proxies root, admin, API, operations, media, and RabbitMQ management paths to named
upstreams. Static files are served from shared volume.

Gaps:

- no TLS configuration despite published port 443;
- no healthcheck;
- media volume absent;
- `/static/` enables directory listing;
- RabbitMQ management subpath behavior is not paired with a RabbitMQ path-prefix setting;
- proxy policy has no explicit request/read timeouts or production security headers.

## 9. Auxiliary Infrastructure

### Prometheus and Grafana

Prometheus config expects `prometheus`, `rabbitmq`, and `cadvisor`. Root Compose defines only
RabbitMQ. Prometheus image is buildable but unused; cAdvisor and Grafana services are
absent. Dashboard JSON is not provisioned anywhere. Treat this directory as dormant design
material, not current monitoring.

### pgAdmin

Standalone Compose uses public port 5050, development-grade default credentials, server
mode disabled, hard-coded Docker host gateway, and an external network named
`skaben_skaben_network`. Root Compose creates differently named public/backbone networks,
so attachment is not established by current files. Backup ignore paths use `pg_admin`
while directory is `pgadmin`.

## 10. Prioritized Findings

### P0 — Establish deployed truth and recovery

1. Rotate committed RabbitMQ/MQTT/STOMP credentials; determine actual secret injection and
   public port exposure.
2. Confirm whether root Compose is production, development, or both; inventory external
   TLS/firewall controls.
3. Add and test PostgreSQL/media recovery procedure; decide Redis and RabbitMQ recovery
   requirements from real state ownership.
4. Confirm deployed consumers of all published RabbitMQ/MQTT/WebSocket ports before
   narrowing exposure.

### P1 — Deterministic foundation

1. Fix WSGI target and bootstrap ordering. Separate migration/repair/schema jobs from API
   process startup.
2. Make Compose own application builds or document one canonical immutable-image flow.
3. Split development bind mounts from deployment configuration.
4. Complete environment template with stable Django secret, host/origin, DB, Redis,
   RabbitMQ, and media/static settings.
5. Add readiness checks and correct DB/Redis dependencies for every process.
6. Define non-root runtime, tighter build context, and intentionally pinned image inputs.
7. Make application and infrastructure startable separately and together.
8. Define one production owner for static and media delivery.

### P4 — Reliable messaging boundary

1. Persist RabbitMQ data or explicitly prove broker data is disposable under outbox/replay
   recovery rules.
2. Replace broad legacy permissions/topology with responsibility-owned exchanges, queues,
   retry paths, and DLQs.
3. Add outbox publisher and role-selected worker processes without collapsing queues into
   one catch-all consumer.
4. Upgrade health checks from node ping to topology plus publish/consume readiness.

## 11. Confirmed Compatibility Inputs

- API, scheduler, and four legacy worker roles currently share one application image.
- PostgreSQL hostname is `db`, Redis hostname is `redis`, and RabbitMQ hostname is
  `rabbitmq` inside Compose.
- External device transport currently depends on RabbitMQ MQTT/WebSocket plugins and
  existing MQTT routing contracts.
- Static and media named-volume identity may matter to deployed backup/restore procedures.
- Existing port bindings, broker usernames, and network names are observed configuration,
  not automatically approved target contracts.

## 12. Unverified / Decision Required

- Which Compose file and environment mode run in production.
- Whether an external proxy/firewall provides TLS and restricts published ports.
- Whether RabbitMQ messages/topology must survive `docker compose down` in deployed use.
- Whether Prometheus/Grafana and pgAdmin files are used by external commands or are stale.
- Whether deployed devices use MQTT TLS, Web MQTT, or Web STOMP ports currently exposed.
- Who backs up and restores database/media volumes, at what frequency, and with what tested
  recovery point/time.
- Whether static/media volume names are referenced by host automation outside repository.

## 13. Review Verification

- Root Compose, pgAdmin Compose, Prometheus YAML, RabbitMQ definitions JSON, and Grafana
  dashboard JSON parse successfully.
- `docker compose config --quiet` exits successfully with local environment, but warns
  that `PYTHONPATH` is unset.
- No images were built and no containers were started. Runtime connectivity, permissions,
  health, migration, recovery, and device compatibility remain untested by this review.

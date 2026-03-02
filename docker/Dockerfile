FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential python3-psycopg2 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PROJECT_ROOT=/opt/app \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    RUNNING_IN_DOCKER=True \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /opt/

COPY pyproject.toml uv.lock* ./

RUN uv venv $VIRTUAL_ENV && \
    uv sync --frozen --extra dev --active

FROM builder AS main

ENV PATH="$VIRTUAL_ENV/bin:$PATH" \
    PYTHONPATH="$PROJECT_ROOT/server:$PYTHONPATH"

WORKDIR ${PROJECT_ROOT}

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY . ${PROJECT_ROOT}
COPY --chmod=755 entrypoint.sh /opt/app/entrypoint.sh

EXPOSE 8000

CMD ["/opt/app/entrypoint.sh"]
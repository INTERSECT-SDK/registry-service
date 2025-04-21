# see https://docs.astral.sh/uv/guides/integration/docker/#optimizations

ARG REPO=
FROM ${REPO}python:3.12-slim AS base

WORKDIR /app

# don't allow python to buffer stdin/stdout
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

FROM base AS builder

ENV UV_COMPILE_BYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install (required) dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --frozen --locked --no-install-project --no-editable

# Sync the project
COPY intersect_registry_service intersect_registry_service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen --locked --no-editable

FROM base AS final

COPY --from=builder --chown=app:app /app/.venv /app/.venv

COPY migrations migrations
COPY alembic.ini alembic.ini
COPY intersect_registry_service intersect_registry_service

# override CMD at container runtime for tests
# note that you generally will NOT want to set UVICORN_WORKERS if running in a Kubernetes cluster, let Kubernetes handle that for you
CMD ["sh", "-c", "fastapi run intersect_registry_service/main.py --workers ${UVICORN_WORKERS:-1}"]


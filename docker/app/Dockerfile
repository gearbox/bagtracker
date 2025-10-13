# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Install the project into `/app`
WORKDIR /app

# Copy dependency files and version script
COPY pyproject.toml uv.lock ./
COPY scripts/extract_version.py ./scripts/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies
# RUN --mount=type=cache,target=/root/.cache/uv \
#     --mount=type=bind,source=uv.lock,target=uv.lock \
#     --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#     uv sync --frozen --no-dev
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Extract version and create version file
RUN python scripts/extract_version.py

# Runtime stage - no pyproject.toml here
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

COPY ./alembic.ini /app/alembic.ini
COPY ./static /app/static

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy version file (not pyproject.toml)
COPY --from=builder /app/backend/_version.py /app/backend/
COPY ./backend /app/backend

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

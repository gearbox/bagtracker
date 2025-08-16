# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app
COPY ./static /app/static

ENV PYTHONUNBUFFERED=1

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

ADD ./backend /app/backend
# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY ./pyproject.toml /app/pyproject.toml
COPY ./uv.lock /app/uv.lock    

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the FastAPI application by default
# Uses `fastapi dev` to enable hot-reloading when the `watch` sync occurs
# Uses `--host 0.0.0.0` to allow access from outside the container
#CMD ["fastapi", "dev", "--host", "0.0.0.0", "backend/asgi.py"]

#CMD ["fastapi", "run", "backend/asgi.py", "--proxy-headers", "--port", "80"]
#CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:80", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-", "backend.asgi:app"]
CMD gunicorn -w $UVICORN_WORKERS -k uvicorn.workers.UvicornWorker -b $BACKEND_HOST:$BACKEND_PORT --timeout 180 --access-logfile - --error-logfile - backend.asgi:app
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY ./static /app/static

# copy and install requirements
COPY ./requirements.txt /app/requirements.txt
COPY ./pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./backend /app/backend

#CMD ["fastapi", "run", "backend/asgi.py", "--proxy-headers", "--port", "80"]
#CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:80", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-", "backend.asgi:app"]
CMD gunicorn -w $UVICORN_WORKERS -k uvicorn.workers.UvicornWorker -b $BACKEND_HOST:$BACKEND_PORT --timeout 180 --access-logfile - --error-logfile - backend.asgi:app
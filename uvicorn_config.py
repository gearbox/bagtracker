"""
Production Uvicorn configuration
Alternative to command-line arguments for better control
"""

import multiprocessing
import os

# Server binding
host = os.getenv("BACKEND_HOST", "0.0.0.0")
port = os.getenv("BACKEND_PORT", "80")
bind = f"{host}:{port}"

# Worker processes
workers = int(os.getenv("UVICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Logging
log_level = os.getenv("LOGGING_LEVEL", "info").lower()
access_log = True

# Timeouts
timeout_keep_alive = 180
timeout_notify = 30

# Performance
backlog = 2048
limit_concurrency = 1000
limit_max_requests = 10000  # Restart workers after N requests (memory leak prevention)

# SSL
ssl_keyfile = os.getenv("SSL_KEYFILE")
ssl_certfile = os.getenv("SSL_CERTFILE")

# Development settings (override in production)
reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
reload_dirs = ["backend"] if reload else None

# Headers
forwarded_allow_ips = "*"  # Trust all proxies (adjust for your setup)
proxy_headers = True

# Config dict for programmatic use
config = {
    "app": "backend.asgi:app",
    "host": host,
    "port": int(port),
    "workers": workers,
    "log_level": log_level,
    "access_log": access_log,
    "timeout_keep_alive": timeout_keep_alive,
    "backlog": backlog,
    "limit_concurrency": limit_concurrency,
    "limit_max_requests": limit_max_requests,
    "forwarded_allow_ips": forwarded_allow_ips,
    "proxy_headers": proxy_headers,
}

if ssl_keyfile and ssl_certfile:
    config |= {
        "ssl_keyfile": ssl_keyfile,
        "ssl_certfile": ssl_certfile,
    }

if reload:
    config |= {
        "reload": True,
        "reload_dirs": reload_dirs,
    }

# This file is used to configure the gunicorn server
import os

# Server socket
bind = f"{os.environ.get("BIND_HOST", "0.0.0.0")}:{os.environ.get("BIND_HOST_PORT", "8080")}"

# The number of worker threads for handling requests
threads = int(os.environ.get("WORKER_THREADS", "4"))
# The number of worker processes for handling requests
workers = "1"
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 60
loglevel = "debug"
# The maximum number of requests a worker will process before being replaced
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = f"{os.getcwd()}/log/access.log"
# access_log_format = '{"remote_ip":"%(h)s","request_id":"%({X-Request-Id}i)s","response_code":"%(s)s","request_method":"%(m)s","request_path":"%(U)s","request_querystring":"%(q)s","request_timetaken":"%(D)s","response_length":"%(B)s"}'

errorlog = f"{os.getcwd()}/log/error.log"

# Process naming
proc_name = os.environ.get("APP_NAME", "gunicorn")

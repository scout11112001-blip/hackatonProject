"""gunicorn settings for the deanery prototype (loaded with -c deploy/gunicorn.conf.py).

Workers: 2 for 1 vCPU / 1 GB RAM. Bigger server: min(2 * vCPU + 1, (free RAM MB - 300) // 90),
set GUNICORN_WORKERS in /etc/deanery/deanery.env.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = max(1, int(os.environ.get("GUNICORN_WORKERS", "2")))
timeout = 30
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
control_socket_disable = True

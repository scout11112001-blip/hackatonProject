"""gunicorn settings for the deanery prototype (loaded with -c deploy/gunicorn.conf.py).

Workers: 5 for 2 vCPU / ~2 GB RAM: min(2 * vCPU + 1, (free RAM MB - 300) // 90) = min(5, 13).
Other server: set GUNICORN_WORKERS in /etc/deanery/deanery.env by the same formula.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = max(1, int(os.environ.get("GUNICORN_WORKERS", "5")))
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
# Trust only the scheme header that nginx always overwrites (PT1-F13).
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}

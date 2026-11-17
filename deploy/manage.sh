#!/usr/bin/env bash
# Run a Django management command with the production environment.
# Usage: sudo -u <APP_USER> /srv/deanery/app/deploy/manage.sh <command> [args]
set -euo pipefail
set -a
. /etc/deanery/deanery.env
set +a
cd /srv/deanery/app
exec /srv/deanery/venv/bin/python manage.py "$@"

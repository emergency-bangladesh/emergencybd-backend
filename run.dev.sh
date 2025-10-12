#!/bin/bash

set -e

export DEV_MODE=True

trap 'echo "Caught signal, exiting..."; pkill -f "gunicorn.*8000"; exit' INT TERM
source ./.venv/bin/activate
fuser -k 8000/tcp || true
exec gunicorn --workers 1 --bind 0.0.0.0:8000 passenger_wsgi:application --reload --log-level debug

#!/bin/sh
# Entrypoint shared by every container running this image (gunicorn, the
# Django-Q worker, the Celery worker/beat) -- see the Dockerfile and
# docs/11-implantacao-e-operacoes.md §11.3/§11.7.
#
# Waiting for the database, applying migrations and collecting static files
# here (rather than in docker-compose's `command:` for every service) means
# every service that depends on this image gets the same, single source of
# truth: whichever container happens to start first does the work, and the
# others just wait on the database being reachable and move on once
# migrations are already applied.
set -eu

echo "Waiting for the database..."
python manage.py wait_for_db

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

if [ "${SKIP_COLLECTSTATIC:-false}" != "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

exec "$@"

#!/bin/sh
# Entrypoint shared by every container running this image (gunicorn, the
# Django-Q worker, the Celery worker/beat, and the one-shot `init` service) --
# see the Dockerfile and docs/11-implantacao-e-operacoes.md §11.3/§11.7.
#
# `wait_for_db` runs unconditionally in every container as cheap
# defense-in-depth: docker-compose.local-node.yml / central-node.yml already
# gate every service on `db: condition: service_healthy`, so this should
# rarely have to actually wait, but that guarantee only holds when this image
# is run *through* those compose files -- not for an ad-hoc `docker run`, or a
# Postgres with no healthcheck attached to it.
#
# Migrations and collectstatic, on the other hand, must run exactly *once*
# per `docker compose up`, not once per container: both compose files run
# them here only in their one-shot `init` service, and set
# SKIP_MIGRATIONS=true / SKIP_COLLECTSTATIC=true on every other service
# (which instead depends on `init: condition: service_completed_successfully`
# before starting at all). Without that, concurrent `migrate --noinput` runs
# from multiple containers can race on the same empty schema, and a `web`
# container restarting on its own (restart: always) would otherwise wipe the
# shared static volume nginx serves from (--clear) on every crash, not just
# on first boot.
set -eu

echo "Waiting for the database..."
python manage.py wait_for_db

if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
    # DEBUG-only (see the command itself) -- never creates a hardcoded-
    # credential account on a real deployment. Runs here, in the same
    # once-per-`docker compose up` block as migrations, purely for local
    # dev convenience.
    python manage.py create_dev_superuser
    # Also DEBUG-only and idempotent -- gives `root` (and every other demo
    # user it creates) a full institution to explore locally, without ever
    # touching a real deployment's data.
    python manage.py seed_demo_data
fi

if [ "${SKIP_COLLECTSTATIC:-false}" != "true" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

exec "$@"

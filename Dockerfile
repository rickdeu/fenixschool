# syntax=docker/dockerfile:1
#
# Single image shared by every FenixSchool Django process (gunicorn, the
# Django-Q worker on the local node, the Celery worker/beat on the central
# node) -- see docs/10-stack-tecnologica-e-estrutura-projeto.md §10.1 and
# docs/11-implantacao-e-operacoes.md §11.3. Which extra dependencies get
# installed is controlled by the REQUIREMENTS_FILE build argument, so the
# local-node and central-node images stay isolated from each other despite
# sharing this Dockerfile (see docker-compose.local-node.yml /
# docker-compose.central-node.yml).

ARG PYTHON_VERSION=3.12-slim

FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libpq-dev + build-essential are only needed to build psycopg's C extension;
# they do not make it into the final runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG REQUIREMENTS_FILE=requirements/local_node.txt
COPY requirements/ requirements/
RUN pip install --user -r "${REQUIREMENTS_FILE}"

FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/fenixschool/.local/bin:$PATH \
    # Only a fallback default for an ad-hoc `docker run` with no compose file
    # involved -- every service in docker-compose.local-node.yml /
    # docker-compose.central-node.yml sets this explicitly, and that value
    # always wins over this one.
    DJANGO_SETTINGS_MODULE=config.settings.local_node

# libpq5 is the runtime (non-dev) Postgres client library psycopg needs.
# postgresql-client provides pg_dump/gzip's own dependency-free `pg_dump`
# binary -- apps.core.services.backup_database() (issue #166) runs it from
# here, over the network, since this image (unlike the `db` service's own
# postgres:16-alpine) never has the Postgres *server* itself.
# libpango-1.0-0/libpangocairo-1.0-0/libgdk-pixbuf-2.0-0/libcairo2/libffi8 +
# shared-mime-info + fonts-dejavu-core are WeasyPrint's own runtime
# dependencies (issue #93, docs/10-stack-tecnologica-e-estrutura-projeto.md
# §10.1) -- it is a pure-Python wheel that `dlopen()`s these at import time,
# nothing to compile, so they only belong in this runtime stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        postgresql-client \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        libffi8 \
        libharfbuzz-subset0 \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin fenixschool

# WORKDIR creates /app while still root, so it -- unlike everything COPY
# --chown places inside it -- would otherwise stay root-owned; celery-beat
# (docker-compose.central-node.yml) writes its schedule file straight into
# this directory as the unprivileged `fenixschool` user, so it needs to be
# writable too, not just its contents.
WORKDIR /app
RUN chown fenixschool:fenixschool /app

COPY --from=builder --chown=fenixschool:fenixschool /root/.local /home/fenixschool/.local
COPY --chown=fenixschool:fenixschool . .
COPY --chown=fenixschool:fenixschool scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/staticfiles /app/media /app/backups \
    && chown -R fenixschool:fenixschool /app/staticfiles /app/media /app/backups

USER fenixschool

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
